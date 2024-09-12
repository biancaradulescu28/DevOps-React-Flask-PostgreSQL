
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

## Storage Configuration --image
**HostPath**
* StorageClass
This SC uses the HostPath CSI driver which provides storage on a node. It has immediate volume binding which indicated that PVCs will have volumes bound and allocated immediately on creation. The Volumes are created dynamically and when a PV from this StorageClass is deleted, the associated.

* PersistentVolumeClaim
This PVC uses the hostpath StorageClass to create a storage request of 1GiB, with read-write access, both read from and written to, but only by one node at a time.

**Local**
* StorageClass
This StorageClass uses ```kubernetes.io/no-provisioner``` which means that automatically create storage but expects you to set it up manually. It uses WaitForFirstConsumer, meaning it will only assign the storage to a pod after the pod is scheduled to run on a node. This ensures that the volume is bound to a node that will actually use it.

* PersistentVolumeClaim
This PVC requests as well 1 GiB of storage with ReadWriteOnce access mode. The storageClassName is set to local-storage, indicating that the PVC is using the previously defined local-storage StorageClass.

* PersistentVolume
The PV uses the local-storage StorageClass, which means the storage is manually set up. It can be accessed by a single node at a time with read-write permissions. It provides 5 GiB of storage which is located on a specific node named minikube-m02. The nodeAffinity ensures that the volume is only available on the specified node.

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
* **Prometheus**
Prometheus monitors and collects metrics about the cluster’s performance and resource usage, stores the data, and can alert users about issues. It helps track system health and performance.
``` 
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus
kubectl expose service prometheus-server --type=NodePort --target-port=9090 --name=prometheus-server-ext

```

* **Grafana**
Grafana is used to visualize the metrics collected by Prometheus. It connects to Prometheus to create dashboards and graphs, making it easier to monitor and analyze the performance and health of the Kubernetes cluster through visual representations.
```
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install grafana grafana/grafana
kubectl expose service grafana — type=NodePort — target-port=3000 — name=grafana-ext

```
![Screenshot 2024-09-11 211322](https://github.com/user-attachments/assets/1f092f77-fd0a-4155-85e6-45e5616cfb65)

**Dashboards**
I created 2 dashboards:
* Backend dashboard which shows the CPU and Memory usage for backend pods and I also added a pannel for pod restarts metrics. All pannels use different types of charts.
* Postgres dashboards with pannels for CPU and Memory usage for postgres pods and a chart to monitor pod uptime.

## Scaling and Updates
### HorizontalPodAutoscaler
For the backend deployment I created an HPA that dynamically adjusts the number of replicas maintaining a number between 2 and 5 replicas, scaling based on CPU and memory utilization. It keeps the average utilization of both resources at 50%.
I also created an HPA for the posgres statefulSet based on CPU and memory usage, keeping the replicas number between 1 and 5 and the respource utilization around 70%. This ensures that the database cand handle varying loads by sca;ing the number of pods.
The HPA uses the Metrics Server to get resource metrics so I enabled the metrics server addon on minikube using:
``` 
minikube addons enable metrics-server 

``` 
![Screenshot 2024-09-11 212548](https://github.com/user-attachments/assets/1092f1ec-be20-4c42-9070-3208b4fb9e25)

### Rolling Update
Before the rolling update I specified a rollingUpdate strategy. I set maxSurge to allow up top 50% more pods to make sure I can add new pods without making the service less available, and I set maxUnavailable to ensure that no more that 50% of the pods are unavailable at the same time.

Steps:  --images
* Change backend deployment image to a different version
![Screenshot 2024-09-11 175258](https://github.com/user-attachments/assets/da6618bd-4d5f-470d-875c-ace8c21a5713)

* Apply the updated configuration   --image cu v3
![Screenshot 2024-09-11 175315](https://github.com/user-attachments/assets/ec4e9f7f-fe90-4352-9412-bc7d7eb6678f)
![Screenshot 2024-09-11 175857](https://github.com/user-attachments/assets/4c65516a-737e-4b5b-9a85-b87670c0ef87)

* Verify rolling Update
![Screenshot 2024-09-11 175422](https://github.com/user-attachments/assets/8f16aed9-2f94-4e48-bd0e-84d44fb2418f)
![Screenshot 2024-09-11 175510](https://github.com/user-attachments/assets/94456329-927d-44c0-b45c-12dd7095d8ed)

* Rollback
![Screenshot 2024-09-11 175736](https://github.com/user-attachments/assets/c52ac69e-79da-4eb4-9b1f-a5b5a7dd9d49)
![Screenshot 2024-09-11 175634](https://github.com/user-attachments/assets/5212eddc-1385-4ca6-81cb-255f58e8c30e)

* Apply the old configuration
![Screenshot 2024-09-11 175927](https://github.com/user-attachments/assets/466311fa-de79-41d0-8b8a-4210138d78d8)

## Advanced Scheduling
For this step I created a new node to my minikube cluster using the following command:
```
minikube node add
```
![Screenshot 2024-09-11 202900](https://github.com/user-attachments/assets/51b98cec-0037-48d0-90a2-e2d66cf21007)

### Affinity 
* **Pod Affinity**
For the frontend pods I configured affinity rules requiring them to be scheduled on the same nodes as backend pods. This improves communication speed between the frontend and backend Using the In operator the label selector will match the values in the list of labels, in this case frontend. And ```requiredDuringSchedulingIgnoredDuringExecution``` ensures that the scheduling can not be ignored and if there are no nodes which respect the rules the pods will not start.
* **Pod Anti-Affinity**
I applied the podAntiAffinity for the Postgres database to keep pods with the postgres label on differenet nodes. This reduces the risk of losing all replicas of the database in case of node failure.
### Taints and Tolerations
I tainted my second node using a NoSchedule effect so that pods without a matching toleration will not be scheduled on this node.
```
kubectl taint nodes minikube-m02 key=db:NoSchedule
```
Also in the database statefulset I added tolerations matching the key, value and effect with the taint and using the ```operator:"Egual"``` to specify how the toleration compares the key and value with the taint. Isolating the database on a dedicated node ensures it won't compoete for resources with other pods. This leads to a more predictable and stable perfomance of the database
![Screenshot 2024-09-11 204453](https://github.com/user-attachments/assets/d417ddb1-8670-4a01-ad68-6d523c72d8cc)

## Health Checks and Application Lifecycle
--image when it works
### Liveness
* The backend liveness probe checks if the application is running, else it restarts the container. This probe makes an HTTP GET request to the /liveness endpoint on port 5000 which I configured in ```app.py```:
```
@app.route('/liveness', methods=['GET'])
def health_check():
    return 'Alive', 200
```
* For the fronted I created a liveness probe similar to the backend one which makes an HTTP GET request to the /liveness path on port 80.

### Readiness
* The backend readiness probe checks if the application is ready to receove traffic. If the probe fails traffic to the pod will be stopped until it passes again. This probe is also an HTTP GET request, to the /readiness endpoint on port 5000. This endpoint checks if the application is running and if it can connect to the database.
```
@app.route('/readiness', methods=['GET'])
def readiness_check():
    try:
        conn = get_db_connection()
        conn.close()
        return 'Ready', 200
    except Exception as e:
        return f'Not Ready: {str(e)}', 500
```
* The frontend probe checks if the frontend container is accepting TCP connections on port 80 allowing the probe to fail up to 30 times.
* For the database I created a readiness probe which checks if the PostgrSQL instance is ready to accept connections. I used an exec probe with the ```pg_isready``` command to check the connection status of a PostgreSQL server.

### Startup
The backend startup probe is used to check if the application has started correctly by listening for TCP connections on port 5000. The probe is allwoed to fail 30 times before is considered failed.

**Scenario**

Suppose that after a deployment of the application the PostgreSQL takes longer to initialize. Without the readiness probe on the database the backend could start sending requests to the database causing failed queries. Also the readiness probe on the backend will check if it can connect and avoid errors for users trying to interact with the application.
The readiness probe the frontend service will also check if it can connect with the backend. If the backend is not ready the probe will fail and the frontend won't start sending traffic. 