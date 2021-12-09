# Git branch to use off of main or development:
`git checkout -b app-engine` - this way you can test it out in the resulting Cloud Build trigger.

# Setting up a GCP Project

1. Google Cloud Platform provides a list of instructions for creating a project here: [GCP's Instructions for Creating a Project](https://cloud.google.com/appengine/docs/standard/nodejs/building-app/creating-project) The following list are notes that correspond to specific steps in the process listed in the link. 

Name the project peerlogic-api-<environment>, such as peerlogic-api-dev and peerlogic-api-demo. In the *Location* field, Place it into the corresponding folder location (peerlogic-dev or peerlogic-demo, etc.) This is how we are organizing environment resources.

2. Please note that there can be a time lag between the time that you create a project and when it actually appears in the list of available projects for your organization. For example, your project may appear in the list of your recent projects in your account yet a colleague may be logged into their account and not see it in the project list.

3. Make sure that the admin for your organization enables billing for the project. 

4. Create app in app engine. **Our organization chooses region us-west4 for its projects.** Choose "Python3.9" as the Language and "Standard" as the environment.


## app.yaml info

We created the app.yaml in the root level of our project using thse 2 sources:
* GCP basic reference here [GCP app.yaml example](https://cloud.google.com/appengine/docs/standard/nodejs/config/appref)


# Deploying to App Engine

If the previous steps have already been completed you are now ready to run `gcloud init`.

1. Re-initialize your default configuration
2. Set the project to the one you created (As mentioned earlier, there can be a time delay for a newly created project to appear in the list of your organization's projects.)
3. Confirm your email login
4. Do you want to configure a default Compute Region and Zone?
   * Hit `Y` and then enter
   * Set the zone to `us-west4-a`
5. Create an environment file  `./deployment/<PROJECT_ID>.env` with the project id you chose above
6. Run `gcloud secrets create peerlogic-api-env --data-file=/path/to/your/environment/file`
7. Uncomment all lines in this file (\*except this one) if running for the first time `./deployment/gcloud_deploy.bash` and then run it from the root of this repository.
   * \* Except for this line - At the time of this writing Celery does not work in App Engine Standard because it cannot connect to Redis. See [JIRA ticket](https://peerlogictech.atlassian.net/browse/PTECH-1011) for this.)
8. Escape any funny characters in your `./deployment/<PROJECT_ID>.env` file that bash doesn't like with " " around the value after the `=` sign.
9.  Run `./deployment/cloud_sql_proxy.bash` and `./deployment/psql_deploy.bash` in another terminal.
10. Verify your peerlogic-api works in the environment you're using by going to Logging in the console.cloud.google.com and running a couple of GET and POST calls.

## Troubleshooting Deploys

If you get the following error, just Retry the build:

```
ERROR: (gcloud.app.deploy) NOT_FOUND: Unable to retrieve P4SA: [service-############@gcp-gae-service.iam.gserviceaccount.com] from GAIA. Could be GAIA propagation delay or request from deleted apps.
```

## Associate Custom Domain to deployed website

**If you did not git init correctly and create your App Engine in us-west4 this portion will not work.** If that is the case, it's best to scrap the project and redeploy using the proper region/zone.

1. Go to [App Engine Application Settings](https://console.cloud.google.com/appengine/settings)

2. Click on Custom Domains and Add a custom domain. Select peerlogic.tech. Remove www.peerlogic.tech and peerlogic.tech. Enter in the name of the service, like `peerlogic-api-dev` and append `.peerlogic.tech`. I used `api-dev.peerlogic.tech` for development. Click Save Mappings. There will be info about the nameservers and A and AAAA records to enter into the DNS zones. This has been done already elsewhere. Take note of the CNAME - this is the one that we will be entering soon. Hit Done.

3. Select the peerlogic-dns Project from the project dropdown, and then go to Cloud DNS. Click peerlogic-tech. Click "Add Record Set".

4. On Create record set page, enter the subdomain (in my case, `peerlogic-api-dev`) into the DNS Name field. In Resource Record Type, select CNAME. In Canonical name 1, enter `ghs.googlehosted.com`. GCP will figure it out from this. Hit Create.

5. Select your project in the dropdown again  and go back to the [App Engine Application Settings](https://console.cloud.google.com/appengine/settings). Click Custom domains. Under SSL security you will see a rotating progress circle. Keep an eye on this. It takes a lot of time for DNS to propogate and for the SSL cert to finish. When the circle is finished, the DNS may still be propogating and not responding at your url yet. Just be patient and i
