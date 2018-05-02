LEASE NOTE:
Please use the python scripts as a point of reference ONLY.

The live lambda function codes should be stored in a S3 bucket in a zip format with a well known name like "opsworkscm-server-mgmt-lambdafunctions.zip" so that it can be referenced by cloudformation and it can be deployed while cloudformation is running.

zipupandsend.sh script reads from ../opsworkscm-server-mgmt-pipeline-params.json file and look for "LambdaS3Bucket" and "LambdaS3Key" parameter keys.  The script uses the values of those keys to send the zip file that contains the lambda functions.
