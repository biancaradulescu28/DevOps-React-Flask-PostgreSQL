
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
### Pod Disruption Budgets
For the backend service I configured the PDB with with ``` maxUnavailable: 1 ``` so only one pod can be inactive in the case of a volutary disruption. The backend handles more data and requests so limiting the number of unavailable pods ensures thhat the application still works properly and has minimal downtime /
In the PDB for the frontend, by setting ``` minAvailable:1 ``` it ensures that at least one frontend pod remains active during disruptions, allowing users to still access the service.

### Quality of service
* **Backend-Burstable**
QoS of type Burstable means that the backend service has minimal requires but can consume more resources if needed. The backend needs flexibility to handle different requests.
* **Frontend-BestEffort**
This offers the frontend service maximum flexibility. As it only displays names from the database it has minimal resource requirements and this allows efficient resource yutilization without having the need for guaranteed resources.
* **Batabase-Guaranteed**
A database needs constant resources to ensure stability and avoid performance issues.


## Resource Management
### Limit Ranges
The Limit of type Container sets the resource consumotion boundaries for each container within the myapp namespace. 
* **Default Requests and Limits**
CPU and memory requests ensure that each container gets a minimum amount of resources, corresponding to the Burstable QoS class for the backend pods. CPU and memory limit define the maximum resources the containers are allowd to use, keeping containers under control with the same numbers as the backend pods.
* **Min and Max Resource Constraints**
CPU and memory min ensure that no container under-provisions its resource requests, preventing performance issues. And max limits the resource requests to prevent from over-claiming.

### Resource Quota
The CPU requests and limits set how much CPU the namespace can request and use the numbers are set to fit all the resources in the myapp namespace. And the memory requests and limits restrict the total memory consumption. ``` pods: "10" ``` limit the total number of pods and the number was set to be higher the the number of the current pods generated. 

## Advanced Networking
* **Backend Network Policy**
This Policy allows traffic from frontend to the backend pod on port 5000 and traffic from the backend pod to tha database pod on port 5432. 
* **Frontend Network Policy**
The frontend can communicate withe tha backend only on port 5000
* **Database Network Policy**
Tis allows traffic from the backend pod to the database pod on port 5432
I also configured two Default Deny Policies, one for backend and one fo the database to deny all ingress traffic to the pods.
---image

## Monitoring and Logging
* **Install Prometheus**
``` 
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus
kubectl expose service prometheus-server --type=NodePort --target-port=9090 --name=prometheus-server-ext

```

* **Install Grafana**
```
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install grafana grafana/grafana
kubectl expose service grafana — type=NodePort — target-port=3000 — name=grafana-ext

```

## Scaling and Updates
### HorizontalPodAutoscaler
For the backend deployment I creted an HPA that dynamically adjusts the number of replicas maintaining a number between 2 and 5 replicas, scaling based on CPU and memory utilization. It keeps the average utilization of both resources at 50%.
The HPA uses the Metrics Server to get resource metrics so I enabled the metrics server addon on minikube using:
``` 
minikube addons enable metrics-server 

``` 
--image
### Rolling Update
Before the rolling update I specified a rollingUpdate strategy. I set maxSurge to allow up top 50% more pods to make sure I can add new pods without making the service less available, and I set maxUnavailable to ensure that no more that 50% of the pods are unavailable at the same time.

Steps:  --images
* Update backend deployment image
```
kubectl set image deployment/backend -n myapp api=biancaradulescu/a2-backend:v3
```
* Apply the updated configuration   --image cu v3
```
kubectl apply -f ./appchart/templates/backend-deployment.yaml
```
* Verify rolling Update
```
kubectl rollout status deployment/backend -n myapp
kubectl rollout history deployment/backend -n myapp
```
--si imagine cu history
* Rollback
```
kubectl rollout undo deployment/backend -n myapp
```
--imagine si cu history
* Apply the old configuration   --image cu v4
```
kubectl apply -f ./appchart/templates/backend-deployment.yaml
```

## Advanced Scheduling
For this step I created a new node to my minikube cluster using the following command:
```
minikube node add
```
--imagine noduri
### Affinity 
* **Pod Affinity**
For the frontend pods I configured affinity rules requiring them to be scheduled on the same nodes as backend pods. This improves communication speed between the frontend and backend Using the In operator the label selector will match the values in the list of labels, in this case frontend. And ```requiredDuringSchedulingIgnoredDuringExecution``` ensures that the scheduling can not be ignored and if there are no nodes which respect the rules the pods will not start.
* **Pod Anti-Affinity**
I applied the podAntiAffinity for the Postgres database to keep pods with the postgres label on differenet nodes. This reduces the risk of losing all replicas of the database in case of node failure.
### Taints and Tolerations
I tainted my second node using a NoSchedule effect so that pods without a matching toleration will not be scheduled on this node. --image
```
kubectl taint nodes minikube-m02 key=db:NoSchedule
```
Also in the database statefulset I added tolerations matching the key, value and effect with the taint and using the ```operator:"Egual"``` to specify how the toleration compares the key and value with the taint. Isolating the database on a dedicated node ensures it won't compoete for resources with other pods. This leads to a more predictable and stable perfomance of the database

--image din nod