# IAM roles and policies

Following are Roles and customer managed policies written for the pipeline

## Lambda function 1: opsworkscm-server-mgmt-lambda1
(Following AWS managed policies are attached)
```text
AmazonS3FullAccess                  (AWS managed policy)
AWSCodePipelineCustomActionAccess   (AWS managed policy)
AWSLambdaBasicExecutionRole         (AWS managed policy)
```

## Lambda function 2: opsworkscm-server-mgmt-lambda2
(Following AWS managed policies are attached)
```text
AmazonEC2FullAccess                 (AWS managed policy)
AmazonS3FullAccess                  (AWS managed policy)
AWSCodePipelineCustomActionAccess   (AWS managed policy)
AWSLambdaBasicExecutionRole         (AWS managed policy)
```

## CodePipeline Policy (Customer managed policy): oneClick_AWS-CodePipeline-Service_generic
(This policy is to be attached to the codepipeline IAM role)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:GetBucketVersioning"
            ],
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Action": [
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::codepipeline*",
                "arn:aws:s3:::elasticbeanstalk*"
            ],
            "Effect": "Allow"
        },
        {
            "Action": [
                "codecommit:CancelUploadArchive",
                "codecommit:GetBranch",
                "codecommit:GetCommit",
                "codecommit:GetUploadArchiveStatus",
                "codecommit:UploadArchive"
            ],
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Action": [
                "codedeploy:CreateDeployment",
                "codedeploy:GetApplicationRevision",
                "codedeploy:GetDeployment",
                "codedeploy:GetDeploymentConfig",
                "codedeploy:RegisterApplicationRevision"
            ],
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Action": [
                "elasticbeanstalk:*",
                "ec2:*",
                "elasticloadbalancing:*",
                "autoscaling:*",
                "cloudwatch:*",
                "s3:*",
                "sns:*",
                "cloudformation:*",
                "rds:*",
                "sqs:*",
                "ecs:*",
                "iam:PassRole"
            ],
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Action": [
                "lambda:InvokeFunction",
                "lambda:ListFunctions"
            ],
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Action": [
                "opsworks:CreateDeployment",
                "opsworks:DescribeApps",
                "opsworks:DescribeCommands",
                "opsworks:DescribeDeployments",
                "opsworks:DescribeInstances",
                "opsworks:DescribeStacks",
                "opsworks:UpdateApp",
                "opsworks:UpdateStack"
            ],
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Action": [
                "cloudformation:CreateStack",
                "cloudformation:DeleteStack",
                "cloudformation:DescribeStacks",
                "cloudformation:UpdateStack",
                "cloudformation:CreateChangeSet",
                "cloudformation:DeleteChangeSet",
                "cloudformation:DescribeChangeSet",
                "cloudformation:ExecuteChangeSet",
                "cloudformation:SetStackPolicy",
                "cloudformation:ValidateTemplate",
                "iam:PassRole"
            ],
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Action": [
                "codebuild:BatchGetBuilds",
                "codebuild:StartBuild"
            ],
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
```

## CodePipeline Role: AWS-CodePipeline-Service 
This role must attach a customer managed policy named "oneClick_AWS-CodePipeline-Service_generic"

## CodeBuild Policy (Customer managed policy): CodeBuildTrustPolicy-opsworkscm-server-mgmt
(This policy is to be attached to the codebuild IAM role)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "logs:CreateLogStream",
                "logs:CreateLogGroup",
                "logs:PutLogEvents",
                "ssm:GetParameters",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::codepipeline-*",
                "arn:aws:ssm:*:121895852041:parameter/CodeBuild/*",
                "arn:aws:logs:*:121895852041:log-group:*",
                "arn:aws:logs:*:121895852041:log-group:*:*"
            ],
            "Effect": "Allow"
        },
        {
            "Action": [
                "iam:PassRole",
                "opsworks-cm:*"
            ],
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
```

## CodeBuild Role: code-build-opsworkscm-mgmt-service-role
This role must attach a customer managed policy named "CodeBuildTrustPolicy"

## OpsWorks CM Service Role: aws-opsworks-cm-service-role
(Following AWS Managed Policy must be attached)
```
AWSOpsWorksCMServiceRole 
```

## OpsWorks CM Instance Profile and Role:
###Instance Profile:
```text
arn:aws:iam::${ACCOUNTID}:instance-profile/aws-opsworks-cm-ec2-role
```

###Instance Profile Role:
```text
arn:aws:iam::${ACCOUNTID}:role/aws-opsworks-cm-ec2-role
```
and the role must attach the following policies
```text
AmazonEC2RoleforSSM                 (AWS managed policy)
AWSOpsWorksCMInstanceProfileRole    (AWS managed policy)
```

##NOTE:
delta-dev-IAM.template is a cloudformation template that creates all the required IAM roles/policies mnentioned in this documewnt.

