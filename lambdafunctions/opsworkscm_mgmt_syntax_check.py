# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import boto3
import zipfile
import re
import types
from botocore.client import Config


def boto3_agent_from_sts(agent_service, agent_type, region, credentials=None):
    if credentials is None:
        credentials = dict()

    session = boto3.session.Session()

    # Generate our kwargs to pass
    kw_args = {
        'region_name': region,
        'config': Config(signature_version='s3v4')
    }

    if credentials:
        kw_args['aws_access_key_id'] = credentials['accessKeyId']
        kw_args['aws_secret_access_key'] = credentials['secretAccessKey']
        kw_args['aws_session_token'] = credentials['sessionToken']

    # Build our agent depending on how we're called.
    if agent_type == 'client':
        return session.client(
            agent_service,
            **kw_args
        )
    if agent_type == 'resource':
        return session.resource(
            agent_service,
            **kw_args
        )


def determine_region(context):
    myregion = context.invoked_function_arn.split(':')[3]

    if myregion:
        return myregion
    else:
        raise RuntimeError(
            'Could not determine region from arn {}'.format(
                context.invoked_function_arn
            )
        )


def determine_account_id(context):
    account_id = context.invoked_function_arn.split(':')[4]
    if account_id:
        return account_id
    else:
        raise RuntimeError(
            'Could not determine account id from arn {}'.format(
                context.invoked_function_arn
            )
        )


def read_artifact_as_config(event, client):
    input_artifact = event['CodePipeline.job']['data']['inputArtifacts'][0]
    artifact_location = input_artifact['location']['s3Location']

    client.download_file(
        artifact_location['bucketName'],
        artifact_location['objectKey'],
        '/tmp/artifact.zip'
    )

    zf = zipfile.ZipFile('/tmp/artifact.zip')

    for filename in zf.namelist():
        if filename == 'opsworkscmconfig.json':
            return json.loads(zf.read(filename))

    raise RuntimeError('Unable to find opsworkscmconfig.json in build artifact output')

def quit_pipeline(event, agent, successful, message):
    print('message is: %s' % message)

    if not successful:
        print("Problem detected during syntax checking. Stopping the pipeline")
        # On exception we will termiante our pipeline.
        agent.put_job_failure_result(
            jobId=event['CodePipeline.job']['id'],
            failureDetails={
                'type': 'JobFailed',
                'message': message
            }
        )
        exit(1)

    else:
        print('Syntax checking passed.  Continuing with the next stage of the pipeline')
        # Build our kwargs for codepipline job result.
        job_result_kwargs = dict(jobId=event['CodePipeline.job']['id'])
        job_result_kwargs['executionDetails'] = {
            'summary': message
        }
        agent.put_job_success_result(
            **job_result_kwargs
        )
        exit(0)


def main(event, context):
    print(
        'Raw event: {}'.format(
            json.dumps(event)
        )
    )

    local_region = determine_region(context)
    local_account = determine_account_id(context)

    print('region is: %s' % local_region)
    print('account is: %s' % local_account)

    # Create connection to codepipeline so as to send exceptions (if any)
    cp_c = boto3_agent_from_sts('codepipeline', 'client', local_region)

    # # # Parse through the json file and go through the "instance" configuration
    # First, we need to Extract our credentials and locate our artifact from our build.
    credentials = event['CodePipeline.job']['data']['artifactCredentials']
    artifact_s3_c = boto3_agent_from_sts(
        's3',
        'client',
        local_region,
        credentials
    )

    try:
        config_file = read_artifact_as_config(event, artifact_s3_c)
        print('Config_file loaded: {}'.format(json.dumps(config_file)))
    except:
        quit_pipeline(event, cp_c, False, 'Could not connect to S3 or failed to access the config file')

    ### Following is a global configuration therefore does not need to be part of the ops_env entry loops
    ### ops_delete_if_absent_entry: Boolean
    try:
        delete_if_absent = config_file['ops_delete_if_absent_entry']
        if delete_if_absent != "True" and delete_if_absent != "False":
            message="You must specify boolean value for the ops_delete_if_absent_entry parameter.\n I was given %s" % delete_if_absent
            quit_pipeline(event, cp_c, False, message)
    except KeyError:
        print "ops_delete_if_absent_entry option not present. Assuming ops_delete_if_absent_entry == False"

    # Loop through ops_env objects in the json file and ensure that we all necessary fields defined
    # namely required fields are: ops_account and ops_region
    #        optional field is  : ops_key_pair_name
    namehash = dict()
    for configparam in config_file['ops_env']:
        opsname = configparam['name']
        opsengine = configparam['ops_engine']
        opsaccount = configparam['ops_account']
        opsregion = configparam['ops_region']
        opssubnet = configparam['ops_subnet']

        print("Checking config for opsname '{}': ".format(opsname))

        # Check whether the name has been taken already or not
        if opsname in namehash:
            message="ERROR: Duplicate name '{}' detected in the opsworkscmconfig.json file".format(opsname)
            quit_pipeline(event, cp_c, False, message)
        else:
            namehash[opsname] = True

        # if opsaccount or opsregion is not defined, fail the pipeline for improper configuration
        if not opsengine or not opsaccount or not opsregion or not opssubnet:
            message="Necessary parameters ops_engine, ops_account, ops_region  or ops_subnet for the opsname '{}' are not present".format(opsname)
            quit_pipeline(event, cp_c, False, message)

        if opsengine != "Chef" and opsengine != "Puppet":
            message="Acceptable parameter values for ops_engine is either Chef or Puppet (case sensitive).  I was given %s" % opsengine
            quit_pipeline(event, cp_c, False, message)

        # These are optional values but when present, they have to have the right values
        ###  ops_engine_model: "Single" if "ops_engine" value is "Chef".  "Monolithic" if "ops_engine" value is "Puppet"
        ###  ops_engine_version: "12" if "ops_engine" value is "Chef".  "2017" if "ops_engine" value is "Puppet"
        ###  ops_region: The supported regions are listed here https://docs.aws.amazon.com/general/latest/gr/rande.html#opsworks_region
        ###  ops_instance_type: [t2.medium and greater, m4.*, or c4.xlarge and greater]
        ###  ops_maintenance_window: [String in DDD:HH:MM format]
        ###  ops_use_automated_backup: [Boolean]
        ###  ops_backup_retention: [Integer up to and including 30],
        ###  ops_backup_window: [String in DDD:HH:MM or HH:MM format]

        # Start with the "ops_engine" value and determine whether the right value has been passed
        try:
            engine_model = configparam['ops_engine_model']
            if (opsengine == "Chef" and engine_model != "Single") or (opsengine == "Puppet" and engine_model != "Monolithic"):
                message="You did not specify correct ops_engine_model for the ops_engine %s. Accepted values are either 'Single' for Chef or 'Monolithic' for Puppet (case sensitive)" % opsengine
        except KeyError:
            # This is OK.  We'll use default
            print "ops_engine_model is not specified using the default"
        
        try:
            engine_version = configparam['ops_engine_version']
            if (opsengine == "Chef" and engine_version != "12") or (opsengine == "Puppet" and engine_version != "2017"):
                message="You did not specify correct ops_engine_version for the ops_engine %s. Specified version %s is not valid for %s" % (opsengine,engine_version,opsengine)
        except:
            # This is OK.  We'll use default
            print "ops_engine_version is not specified using the default"

        ## Currently only following regions support opsworks-cm:
        ## us-east-1, us-east-2, us-west-1, us-west-2, ap-northeast-1, ap-southeast-1, ap-southeast-2, eu-central-1, eu-west-1
        opsworks_supported_region = {
            "us-east-1": True,
            "us-east-2": True,
            "us-west-1": True,
            "us-west-2": True,
            "ap-northeast-1": True,
            "ap-southeast-1": True,
            "ap-southeast-2": True,
            "eu-central-1": True,
            "eu-west-1": True
        }
        try:
            supported_region=opsworks_supported_region[opsregion]
        except KeyError:
            message="Region %s does not support OpsWorks Configuration Manager yet" % opsregion
            quit_pipeline(event, cp_c, False, message)

        # Following is supported instance types for OpsWorks CMs taken from:
        #  https://docs.aws.amazon.com/opsworks-cm/latest/APIReference/API_CreateServer.html#opsworkscm-CreateServer-request-InstanceType
        opsworks_supported_instance_type = {
            "m4.large": "Chef",
            "c4.large": "Puppet",
            "c4.xlarge": "Puppet",
            "c4.2xlarge": "Puppet",
            "r4.xlarge": "Chef",
            "r4.2xlarge": "Chef"
        }
        try:
            instancetype=configparam['ops_instance_type']
            try:
                #supportedinstancetype=opsworks_supported_instance_type[instancetype]
                if opsworks_supported_instance_type[instancetype] == opsengine:
                    print "Specified instance type %s is supported" % instancetype
            except KeyError:
                message="Instance type %s is not supported for OpsWorks Configuration Manager" % instancetype
                quit_pipeline(event, cp_c, False, message)
        except KeyError:
            # We don't have to do anything as default instance type will be assigned
            print "Instance type not passed in for the opsworks-cm instance %s.  Using the Default (m4.large)" % opsname

        ### ops_maintenance_window: [String in DDD:HH:MM format]
        ###  Acceptable regex match for the string is: ^((Mon|Tue|Wed|Thu|Fri|Sat|Sun):)?([0-1][0-9]|2[0-3]):[0-5][0-9]$
        try:
            maintenancewindow = configparam['ops_maintenance_window']
            match = re.match("^((Mon|Tue|Wed|Thu|Fri|Sat|Sun):)?([0-1][0-9]|2[0-3]):[0-5][0-9]$",maintenancewindow)
            if not match:
                message="Improper maintenance window format %s\n Please ensure that the format follows DDD:HH:MM pattern" % maintenancewindow
                quit_pipeline(event, cp_c, False, message)
            print "Maintenance Window string '%s' looks good" % maintenancewindow
        except KeyError:
            # We don't have to do anything as a random maintenance window will be assigned
            pass

        ### ops_use_automated_backup
        ###  Need to ensure that this is boolean
        try:
            use_automated_backup=configparam['ops_use_automated_backup']
            if use_automated_backup != "True" and use_automated_backup != "False":
                message="You must specify boolean value for the ops_use_automated_backup parameter.\n I was given %s" % use_automated_backup
                quit_pipeline(event, cp_c, False, message)
            print "A boolean value has been correctly specified for the ops_use_automated_backup parameter: %s" % use_automated_backup
        except KeyError:
            # The default behaviour is to use automated backup
            pass

        ### ops_backup_retention: [Integer up to and including 30],
        try:
            if type(configparam['ops_backup_retention']) != types.IntType or configparam['ops_backup_retention'] > 30 or configparam['ops_backup_retention'] <= 0:
                message="Backup retention period of %s is not valid.  Remember you can retain up to 30 backups" % configparam['ops_backup_retention']
                quit_pipeline(event, cp_c, False, message)
            print "Retention Period value looks correct: %s" % configparam['ops_backup_retention']
        except KeyError:
            # The default retention period is 30
            pass

        ### ops_backup_window: [String in DDD:HH:MM or HH:MM format]
        try:
            backup_window = configparam['ops_backup_window']
            match = re.match("^((Mon|Tue|Wed|Thu|Fri|Sat|Sun):)?([0-1][0-9]|2[0-3]):[0-5][0-9]$", backup_window)
            if not match:
                message = "Improper Backup window format %s\n Please ensure that the format follows DDD:HH:MM or HH:MM pattern" % backup_window
                quit_pipeline(event, cp_c, False, message)
            print "Backup Window string '%s' looks good" % backup_window
        except KeyError:
            # The default backup window is random any time as the backup activities are non-intrusive
            pass

    message='Configuration file looks good.  Continuing with the next stage of the pipeline'
    quit_pipeline(event, cp_c, True, message)

def lambda_handler(event, context):
    main(event, context)


def outside_lambda_handler():
    class Context(object):
        def __init__(self, **kwargs):
            self.function_name = kwargs.get(
                'function_name',
                'OpsworksCMServerMgmt'
            )
            self.invoked_function_arn = kwargs.get(
                'invoked_function_arn',
                'arn:aws:lambda:us-east-1:121895852041'
                + ':function:OpsWorksCMServerMgmt'
            )
            self.log_group_name = kwargs.get(
                'log_group_name',
                '/aws/lambda/OpsWorksCMServerMgmt'
            )
            self.log_stream_name = kwargs.get(
                'log_stream_name',
                '2018/03/26/[$LATEST]7ea52202c1494810ab5713f045697b4f'
            )

    context = Context()
    event = json.loads("""
{
  "CodePipeline.job": {
    "data": {
      "artifactCredentials": {
        "secretAccessKey": "HZpC+Qucr6gmf1SElpKRYqs3Iip9Tj6FCyoPoVB7",
        "accessKeyId": "ASIAJAGW6Z5LF2HKMNDA",
        "sessionToken": "FQoDYXdzEHcaDAavVXmYGgX/89KAoSKsAVG9QJFB/+a0Ffex7NHTft/IEw2vCRZAqavYP78IqNJwq0ddQBFjXZh1hvOnb7f+awK6g1jDFehSgMhBPFYw9dkqsc2H4GGcTHVgf1ICUqylUmFSq9hBNQ6zRGQuXJ6/wNS1I8IkMAmKHzRpH+69wCwOQKzVygciIoEI6SPJlPEUBeFgM/vYLcgZmoh+dL7GSuz+yrfBVEYQEvU/q8FLWi+txKceavrgm+QCtCYo5Y2C1wU="
      },
      "actionConfiguration": {
        "configuration": {
          "FunctionName": "mylambda"
        }
      },
      "inputArtifacts": [
        {
          "location": {
            "type": "S3",
            "s3Location": {
              "objectKey": "opsworkscm-server-mg/OpsWorksCM/1m8abuj",
              "bucketName": "codepipeline-opsworkscm-stack1"
            }
          },
          "name": "OpsWorksCMmgmt",
          "revision": "4c5375146b7d9b80e53a95f12747007ded4ad7df"
        }
      ],
      "outputArtifacts": []
    },
    "id": "482b288e-8746-42ab-9e6b-7c8e21826d86",
    "accountId": "121895852041"
  }
}
""")
    main(event, context)


if __name__ == '__main__':
    outside_lambda_handler()
