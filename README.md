# SWT-FSE

## Installation

* make sure you have python3.5 installed

* clone the repo, setup virtual environment, and install requirements
```
$ git clone git@github.com:sbour/SWT-FSE.git 
$ cd SWT-FSE
$ git fetch origin fse
$ git checkout fse
$ pyenv venv
$ sudo pip install -r requirements.txt
```


* add mysql username and password to os enviromental variables, such as to your .bash_profile
```
$ vim ~/.bash_profile
$ export RDS_SWT_USERNAME=<username>
$ export RDS_SWT_PASSWD=<pass>
```

* edit the configuration file for your mysql settings (resources/fse/config.ini)

## start the server

```
$ python3.5 server.py
```


## POST to the server

```
$ curl localhost:5000/fse/ -d '{"city": "New York", "state": "NY", "number_extracts": 1, "analysis_type": ["annotation", "variant_analysis"], "sequencing_tech": ["Illumina", "PacBio"]}' -X POST

```

(or use POSTMAN instead of curl (https://www.getpostman.com/))

## Develop the fse algorithm
* fse is in resources/fse/__init__.py
* don't forget to pull before pushing
# UdacityMLhw
