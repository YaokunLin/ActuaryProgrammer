# Dependencies
Install GCP Dependencies to your local machine:
* [gcloud SDK](https://cloud.google.com/sdk/docs/quickstart)
* [1Password CLI](https://support.1password.com/command-line/)
* [psql](https://blog.timescale.com/blog/how-to-install-psql-on-mac-ubuntu-debian-windows/)
* [kustomize v2.0.3](https://github.com/kubernetes-sigs/kustomize/releases/tag/v2.0.3)

Save kustomize with executable permissions.

GKE ships with kubernetes version 1.19 in gcloud installation, which means it ships with kustomize version 2.0.3 at the time of this writing:

Helpful Docs:
* [Kustomize 2.0.3](https://github.com/kubernetes-sigs/kustomize/tree/v2.0.3/docs)

# Creating a new environment

## Create a new project

1. Google Cloud Platform provides a list of instructions for creating a project here: [GCP's Instructions for Creating a Project](https://cloud.google.com/resource-manager/docs/creating-managing-projects) The following list are notes that correspond to specific steps in the process listed in the link.

Name the project peerlogic-api-<environment>, such as peerlogic-api-dev and peerlogic-api-demo. In the *Location* field, Place it into the corresponding folder location (non-production/development-environment/rest-apis, etc.) This is how we are organizing environment resources.

2. Please note that there can be a time lag between the time that you create a project and when it actually appears in the list of available projects for your organization. For example, your project may appear in the list of your recent projects in your account yet a colleague may be logged into their account and not see it in the project list.

3. Make sure that the admin for your organization enables billing for the project.


## Set up gcloud

Run the following command and select the following:

* your new project from the list
* select your login or log in for the first time
* select `us-west4-a` as your default region. If you don't see it listed, type `list` to find it.

```bash
gcloud init
```

## Set Env vars

Obtain the username and password for the [Peerlogic Netsapiens API user](https://start.1password.com/open/i?a=P3RU52IFYBEH3GKEDF2UBYENBQ&v=wlmpasbyyncmhpjji3lfc7ra4a&i=4snjuintsvcurafofmf53twjtm&h=my.1password.com). Have an admin set up a new client ID and secret for this application in core1.

Set environment variables in the root directory stage.env or prod.env (no dev environment). Set the env file in 1Password as "peerlogic-api ENVNAME .env file", like the [peerlogic-api STAGE .env file](https://start.1password.com/open/i?a=P3RU52IFYBEH3GKEDF2UBYENBQ&v=wlmpasbyyncmhpjji3lfc7ra4a&i=xak2xx3lcnapdgsga7qdvxtwfe&h=my.1password.com).

Obtain the username and password for the [Peerlogic Netsapiens API user](https://start.1password.com/open/i?a=P3RU52IFYBEH3GKEDF2UBYENBQ&v=wlmpasbyyncmhpjji3lfc7ra4a&i=4snjuintsvcurafofmf53twjtm&h=my.1password.com). Have an admin set up a new client ID and secret for this application in core1 and copy the link address by right-clicking the item in the list, clicking Share, and "Copy link" and send it to you via slack. Set the NETSAPIENS_CLIENT_ID and NETSAPIENS_CLIENT_SECRET in the <env>.env file you're working with from this entry.

Set the NETSAPIENS_API_USERNAME and NETSAPIENS_API_PASSWORD in the <env>.env file you're working with from the following [1Password Item](https://start.1password.com/open/i?a=P3RU52IFYBEH3GKEDF2UBYENBQ&v=wlmpasbyyncmhpjji3lfc7ra4a&i=4snjuintsvcurafofmf53twjtm&h=my.1password.com)


# Run gcloud deployment script

From the root of this directory:

Activate your virtual environment and `pip install -r requirements/requirements.txt`.

Then run:

```bash
cd ./deployment
.gcloud_deploy.bash
```


## Create the Postgres Database
Test the password by running the cloud_sql_proxy.


After installing the cloud_sql_proxy, add it to your PATH. Then run the following in a new terminal window.
```bash
cloud_sql_proxy -instances="[YOUR_INSTANCE_CONNECTION_NAME]"=tcp:5432
```

In another terminal window, install postgres and then run the following command:

```bash
./deployment/psql_deploy.bash
```

# Create Cloud Build for GKE

Enable Kubernetes Engine - Kubernetes Engine Developer in the [Settings page for GKE](https://console.cloud.google.com/cloud-build/settings/service-account).

Test your build before creating a trigger:

```bash
gcloud builds submit --project=project-id --config cloudbuild.yaml
```

Where:

* project-id is the ID for your project.



## Update GKE kustomization yaml file with the appropriate image name

This is titled kubernetes/overlays/<project_id>/kustomization.yaml

Update the image value with this value:

`gcr.io/<yourenvnamehere>/peerlogic-api`


## Validating Setup of HTTPS Ingress


### Check the reserved static IP works

The gcloud_deploy.bash script at some point will output the following:

```log
Assigning api-env.peerlogic.tech to ADDRESS: 203.0.113.32
```

Check that this matches with the following command:

```bash
kubectl get ingress
```
The output is similar to the following:

```bash
NAME            CLASS    HOSTS   ADDRESS                 PORTS   AGE
basic-ingress   <none>   *       should-match-above-ip   80      54s
```


The load balancer's IP address is listed in the ADDRESS column. If you are using a reserved static IP address that will be the load balancer's address.

If the address is not listed, wait for the Ingress to finish setting up.

### Visiting your reserved static IP address
To verify that the load balancer is configured correctly, you can either use a web browser to visit the IP address or use curl:

```bash
curl http://203.0.113.32/ # substitute your IP from the ADDRESS in the deployment output
```

Note: You might get HTTP 404 and HTTP 500 errors for a few minutes if you used Ingress resource to configure a load balancer. It takes time for configuration changes to propagate to regions across the globe.

### Visiting your domain name
To verify that your domain name's DNS A records resolve to the IP address you reserved, visit your domain name.

`./deployment/cloud_deploy.bash`'s run will output the following:

```text
Domain name api-prod.peerlogic.tech is propagating. All set!
```

Note: It can take a few hours for DNS records to propagate. This time might depend on your nameservers, local internet service provider (ISP), and many other factors.

To make a DNS query for your domain name's A record, run the host command with the output of the domain name from the deployment script similar to the above.

```bash
host api-prod.peerlogic.tech
```

Output:

```text
api-prod.peerlogic.tech has address 34.117.22.142
```

At this point, you can point your web browser to your domain name and visit your website!

### Babysit the Google-managed Certificate
Wait for the Google-managed certificate to be provisioned. This may take up to 60 minutes. You can check on the status of the certificate with the following command:

```bash
kubectl describe managedcertificate CERTIFICATE_NAME
```

Once a certificate is successfully provisioned, the value of the Status.CertificateStatus field will be Active. The following example shows the output of kubectl describe after the certificate is successfully provisioned:


Name:         CERTIFICATE_NAME
Namespace:    default
Labels:       <none>
Annotations:  <none>
API Version:  networking.gke.io/v1
Kind:         ManagedCertificate
(...)
Spec:
  Domains:
    DOMAIN_NAME1
    DOMAIN_NAME2
Status:
  CertificateStatus: Active
(...)


Verify that SSL is working by visiting your domains using the https:// prefix. Your browser will indicate that the connection is secure and you can view the certificate details.

