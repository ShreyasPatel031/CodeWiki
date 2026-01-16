# K8s Helper Module Documentation

## Purpose
The `k8shelper` module provides a set of utility functions and structures to simplify interactions with the Kubernetes API. It acts as an abstraction layer, making it easier for other parts of the system to perform common Kubernetes operations without directly managing the complexities of the Kubernetes client libraries.

## Core Components

### `Ops`
```go
type Ops struct {
	kClient        *kubernetes.Clientset
	kDynamicClient *dynamic.DynamicClient
	logger         *zap.Logger
}
```
The `Ops` struct encapsulates the necessary Kubernetes client interfaces and a logger for operations. It contains:
- `kClient`: A standard Kubernetes `Clientset` for interacting with core Kubernetes resources (e.g., Pods, Deployments).
- `kDynamicClient`: A dynamic Kubernetes `DynamicClient` for interacting with custom resources or resources whose types are not known at compile time.
- `logger`: A `zap.Logger` instance for logging operational details and errors. 

This struct provides a consolidated way to perform various Kubernetes operations, ensuring that clients have access to both static and dynamic API capabilities, along with robust logging.