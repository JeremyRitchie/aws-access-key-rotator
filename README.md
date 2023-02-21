# AWS Access Key Rotator

This is repo is intended to be widely reused as a solution to automatically rotating IAM User Access Keys.

Read more about this repo and how you can best use it here: https://jeremyritchie.com/posts/11/

## Prerequisites

* Python3
* AWS CDK Toolkit
  ```sh
  npm install -g aws-cdk
  ```
## Architecture

![](/secrets-manager-rotation-architecture.png?raw=true)

## Lambda Logic

![](/Secret-Rotation.png?raw=true)




## How to use

`env_config.py` contains most parameters you would want to adjust. When customizing, go there first.


The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization process also creates
a virtualenv within this project, stored under the .venv directory.  To create the virtualenv
it assumes that there is a `python3` executable in your path with access to the `venv` package.
If for any reason the automatic creation of the virtualenv fails, you can create the virtualenv
manually once the init process completes.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
