
# Second Assignment

Deploy and manage a multi-tier application on a Kubernetes cluster. Is simple web application consisting of:
* Frontend: A React.js application 
* Backend: A Python Flask API  
* Database: PostgreSQL

I created a web application which displays in browser a greeting for each name in a users database. After creating the application code in python and react I containerized the application using 2 Dockerfiles: 
* a python image where I am installing the requirements for the flask application
* a node image to run the react application, then copy the built output into an Nginx container to serve the static content on port 80
To test the application I created a docker-compose file to generate the containers.
![Screenshot 2024-09-04 085335](https://github.com/user-attachments/assets/ab3f4683-18ee-44d4-9702-98804d0d23f4)

After testing I pushed the images on Dockerhub:
* ``` biancaradulescu/a2-frontend ```
* ``` biancaradulescu/a2-backend ```
![Screenshot 2024-09-11 205133](https://github.com/user-attachments/assets/81ef8590-4a1e-4eab-9115-d35bc6357021)


## Kubernetes Cluster Setup
I am using Minikube to set up a single-node kubernetes cluster. 
![Screenshot 2024-09-02 151146](https://github.com/user-attachments/assets/1e47238a-6974-43e7-8c79-9f9393d142ba)


## Application Deployment
To manage and deploy the k8s application efficiently I created a helm chart in which I have all the yaml files and a new namespace - **myapp** for all my resources.
### Deployments
* **Backend deployment**
The yaml defines a backend application running in the myapp namespace with 2 replicas. The spec creates a container named api running the backend image pulled from my Dockerhub repository, listens on port 5000 which is the default port for Flask and has the required environment variables to connect to PostgreSQL.
* **Frontend deployment**
The file configures a frontend application in the myapp namespace with 2 replicas. The pod template specifies a container named web runnting the frontend image, which listens on port 80, tipically used for web traffic.
![Screenshot 2024-09-04 093031](https://github.com/user-attachments/assets/25ee0c16-91d8-4f2d-90cb-a0988f14d29c)


I created the deployment configuration by first creating a deployment with ``` dry-run ``` and retrieving its yaml which I edited to meet the needs of my application.
```
kubectl create deployment test --image biancaradulescu/a2-frontend:v1 -o yaml --dry-run
```
### StatefulSet
The configuration defines a single replica of a PostgreSQL database, which uses the ``` postgres:13.16 ``` image and sets the environment variables from aKubernetes secret. The database data is stored in a Persistent Volume, and the initialization scripts are mounted from a ConfigMap.
![Screenshot 2024-09-04 093016](https://github.com/user-attachments/assets/0994b2b5-aabc-4655-b8aa-bfa96e3fbc9b)


### Services
* **Backend service**
This resource defines a ClusterIP service, exposing the backend application within the cluster on port 5000, directing traffic to port 500 in the container.
* **Frontend service**
The yaml configures another ClusterIP service in the myapp namespace, exposing the application on port 80 in the cluster and mapping it to port 80 in the container. The selector field links the service to the corresponding frontend pods
* **Database service**
This K8s service resource defines a Headless service with ``` clusterIP: None ``` each pod getting unique addresses allowing the connection with specific pods. It exposes port 5432 in the cluster and 5432 in the container and connects with the statefulSet for PostgreSQL using the selector.
![Screenshot 2024-09-04 152512](https://github.com/user-attachments/assets/ed66a59d-652e-4a47-9675-ea3d95f1e853)

## Configuration Management
### ConfigMap
The configMap contains SQL scripts to initialize the PostgreSQL database with a ``` users ``` table and some initial data - names. 
In the StatefulSet the ConfigMap is mounted as a volume at ```/docker-entrypoint-initdb.d ```, the directory that PostgreSQL scans on startup to execute the initialization scripts.
![Screenshot 2024-09-04 155417](https://github.com/user-attachments/assets/dd168b26-fb1f-467c-89b4-07f48ee59fb7)


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
![Screenshot 2024-09-04 155430](https://github.com/user-attachments/assets/69c424cd-43bc-415c-ae83-a9eb216ac2cd)

## High Availability and Service Quality
### Pod Disruption Budgets
For the backend service I configured the PDB with ``` maxUnavailable: 1 ``` so only one pod can be inactive in the case of a volutary disruption. The backend handles more data and requests so limiting the number of unavailable pods ensures that the application still works properly and has minimal downtime.
In the PDB for the frontend, by setting ``` minAvailable:1 ``` it ensures that at least one frontend pod remains active during disruptions, allowing users to still access the service.
![Screenshot 2024-09-04 155343](https://github.com/user-attachments/assets/456d968c-9a14-45f0-a27e-16cd2b434005)

### Quality of service
* **Backend-Burstable**
QoS of type Burstable means that the backend service has minimal requirements but can consume more resources if needed. The backend needs flexibility to handle different requests.
* **Frontend-BestEffort**
This offers the frontend service maximum flexibility. As it only displays names from the database it has minimal resource requirements and this allows efficient resource utilization without having the need for guaranteed resources.
* **Batabase-Guaranteed**
A database needs constant resources to ensure stability and avoid performance issues.


## Resource Management
### Limit Ranges
The Limit of type Container sets the resource consumption boundaries for each container within the myapp namespace. 
* **Default Requests and Limits**
CPU and memory requests ensure that each container gets a minimum amount of resources, corresponding to the Burstable QoS class for the backend pods. CPU and memory limit define the maximum resources the containers are allowd to use, keeping containers under control with the same numbers as the backend pods.
* **Min and Max Resource Constraints**
CPU and memory min ensure that no container under-provisions its resource requests, preventing performance issues. And max limits the resource requests to prevent from over-claiming.
![Screenshot 2024-09-11 210651](https://github.com/user-attachments/assets/b4a9cbde-4bed-4a87-a5d1-53a824546063)

### Resource Quota
The CPU requests and limits set how much CPU the namespace can request and use the numbers are set to fit all the resources in the myapp namespace. And the memory requests and limits restrict the total memory consumption. ``` pods: "10" ``` limit the total number of pods and the number was set to be higher the the number of the current pods generated. 
![Screenshot 2024-09-11 210759](https://github.com/user-attachments/assets/5202c374-f180-47a3-a291-17389a96cd1a)


## Advanced Networking
* **Backend Network Policy**
This Policy allows traffic from frontend to the backend pod on port 5000 and traffic from the backend pod to the database pod on port 5432. 
* **Frontend Network Policy**
The frontend can communicate with the backend only on port 5000
* **Database Network Policy**
This allows traffic from the backend pod to the database pod on port 5432
I also configured two Default Deny Policies, one for backend and one to the database to deny all ingress traffic to the pods.
I also added deny policies for backend and database to block all incoming traffic except for what is alloewd by other policies.
![Screenshot 2024-09-11 210930](https://github.com/user-attachments/assets/239940e1-5cea-4fdb-9e2b-e40a1cac0a38)

## Monitoring and Logging
For monitoring and logging I created separate namespaces.
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
![Screenshot 2024-09-11 211322](https://github.com/user-attachments/assets/1f092f77-fd0a-4155-85e6-45e5616cfb65)


## Scaling and Updates
### HorizontalPodAutoscaler
For the backend deployment I created an HPA that dynamically adjusts the number of replicas maintaining a number between 2 and 5 replicas, scaling based on CPU and memory utilization. It keeps the average utilization of both resources at 50%.
I also created an HPA for the posgres statefulSet based on CPU and memory usage, keeping the replicas number between 1 and 5 and the respource utilization around 70%. This ensures that the database cand handle varying loads by sca;ing the number of pods.
The HPA uses the Metrics Server to get resource metrics so I enabled the metrics server addon on minikube using:
``` 
minikube addons enable metrics-server 

``` 

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
