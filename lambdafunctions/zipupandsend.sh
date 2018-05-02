#!/bin/sh

# REQUIREMENT: Cloudformation parameter file ../opsworkscm-server-mgmt-pipeline-params.json must
#              be present and following two entries must have real accessible value
#
#    {
#        "ParameterKey": "LambdaS3Bucket",
#        "ParameterValue": "MYS3BUCKETNAME"
#    },
#    {
#        "ParameterKey": "LambdaS3Key",
#        "ParameterValue": "opsworkscm-server-mgmt-lambdafunctions.zip"
#    }
#
# EXAMPLE: (LambdaS3Bucket) "opsworkscm-lambda-sources-us-east-1"
#          (LambdaS3Key)    "opsworkscm-server-mgmt-lambdafunctions.zip"
#
# ASSUMPTION: aws CLI must be configured and the default profile is pointing to
#             the desired target environment.  Otherwise, please uncomment AWSCLIPROFILE
#             environment variable below and provide appropriate profile name.
#AWSCLIPROFILE="mydesiredawscliprofile"

dests3bucket=`cat ../opsworkscm-server-mgmt-pipeline-params.json | grep -A1 LambdaS3Bucket | grep ParameterValue | cut -d":" -f2 | sed 's/ //; s/"//g'`
dests3objectkey=`cat ../opsworkscm-server-mgmt-pipeline-params.json | grep -A1 LambdaS3Key | grep ParameterValue | cut -d":" -f2 | sed 's/ //; s/"//g'`
srczipfile="/tmp/.lambdafunctions.zip.$$"

zip $srczipfile *.py

# Now upload the zip file to the s3 bucket
[ -n "$AWSCLIPROFILE" ] && AWSCLIPROFILE="--profile $AWSCLIPROFILE"

aws $AWSCLIPROFILE s3 cp $srczipfile s3://$dests3bucket/$dests3objectkey

rm -f $srczipfile
