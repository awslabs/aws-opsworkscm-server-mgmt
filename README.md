## AWS Opsworkscm Server Mgmt

aws-opsworkscm-server-mgmt sets up a pipeline that manages OpsWorks Configuration Manager server instances (such as OpsWorks Chef Automate and/or OpsWorks Puppet Enterprise) based on a configuration file (opsworkscmconfig.json). The pipeline can identify a "rogue" instances (defined by those instances that does not have an entry in the opsworkscmconfig.json) and optionally remove the instances. The pipeline currently supports single account and multi region for now but the effort is under way to support multi account and multi region instances.

## License Summary

This sample code is made available under a modified MIT license. See the LICENSE file.
