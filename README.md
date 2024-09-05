
# Second Assignment

Deploy and manage a multi-tier application on a Kubernetes cluster. Is simple web application consisting of:
* Frontend: A React.js application 
* Backend: A Python Flask API  
* Database: PostgreSQL

I created a web application which displays in browser a greeting for each name in a users database. After creating the application code in python and react I containerized the application using 2 Dockerfiles: 
* a python image where I am installing the requirements for the flask application
* a node image to run the react application, then copy the built output into an Nginx container to serve the static content on port 80
To test the application I created a docker-compose file to generate the containers. ----imagine
After testing I pushed the images on Dockerhub:
* ``` biancaradulescu/a2-frontend ```
* ``` biancaradulescu/a2-backend ```

## Kubernetes Cluster Setup
I am using Minikube to set up a single-node kubernetes cluster. 
---imagine

## Application Deployment
To manage and deploy the k8s application efficiently I created a helm chart in which I have all the yaml files.
### Deployments
* **Backend deployment**
The yaml defines a backend application running in the myapp namespace with 2 replicas. The spec creates a container named api running the backend image pulled from my Dockerhub repository, listens on port 5000 which is the default port for Flask and has the required environment variables to connect to PostgreSQL.
* **Frontend deployment**
The file configures a frontend application in the myapp namespace with 2 replicas. The pod template specifies a container named web runnting the frontend image, which listens on port 80, tipically used for web traffic.
---image

I created the deployment configuration by first creating a deployment with ``` dry-run ``` and retrieving its yaml which I edited to meet the needs of my application.
```
kubectl create deployment test --image biancaradulescu/a2-frontend:v1 -o yaml --dry-run
```
### StatefulSet
The configuration defines a single replica of a PostgreSQL database, which uses the ``` postgres:13.16 ``` image and sets the environment variables from aKubernetes secret. The database data is stored in a Persistent Volume, and the initialization scripts are mounted from a ConfigMap.
---image

### Services
* **Backend service**
This resource defines a ClusterIP service, exposing the backend application within the cluster on port 5000, directing traffic to port 500 in the container.
* **Frontend service**
The yaml configures another ClusterIP service in the myapp namespace, exposing the application on port 80 in the cluster and mapping it to port 80 in the container. The selector field links the service to the corresponding frontend pods
* **Database service**
This K8s service resource defines a Headless services with ``` clusterIP: None ``` each pod getting unique addreses allowing the connection with specific pods. It exposes port 5432 in the cluster and 5432 in the container and connects with the statefulSet for PostgreSQL using the selector.
---image

## Configuration Management
### ConfigMap
The configMap contains SQL scripts to initialize the PostgreSQL database with a ``` users ``` table and some initial data - names. 
In the StatefulSet the ConfigMap is mounted as a volume at ```/docker-entrypoint-initdb.d ```, the directory that PostgreSQL scans on startup to execute the initialization scripts.

### Secrets
The K8s secret stores data necessary for the connection with the PostgreSQL database. The values are base64-encoded. 
In the StatefulSet these secrets are used to provide the values for the environment variables of the PostgreSQL container. This keeps sensitive information secure and separate from the main configuration.
I made this yaml file by first creating a secret using ``` dry-run ```, taking the yaml of the resource and adding the content in my file.
```
kubectl create secret generic postgresql \
  --from-literal POSTGRES_DB="mydb" \
  --from-literal POSTGRES_USER="myuser" \
  --from-literal POSTGRES_PASSWORD="mypassword" -o -yaml --dry-run
```
## High Availability and Service Quality