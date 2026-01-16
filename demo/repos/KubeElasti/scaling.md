# Scaling Module Documentation

## Purpose
The `scaling` module provides the core interfaces and implementations for managing the scaling logic of services within the system. It abstracts the complexities of different scaling mechanisms, allowing for flexible and extensible scaling strategies.

## Core Components

### `Scaler` Interface
```go
type Scaler interface {
	IsHealthy(ctx context.Context) (bool, error)
	ShouldScaleToZero(ctx context.Context) (bool, error)
	ShouldScaleFromZero(ctx context.Context) (bool, error)
	Close(ctx context.Context) error
}
```
The `Scaler` interface defines the contract for any scaling implementation. It includes methods to check the health of a scaler (`IsHealthy`), determine if a service should scale down to zero replicas (`ShouldScaleToZero`), ascertain if a service should scale up from zero replicas (`ShouldScaleFromZero`), and a method to gracefully shut down the scaler (`Close`). This interface ensures that all scaling mechanisms adhere to a common set of behaviors.

### `ScaleHandler`
```go
type ScaleHandler struct {
	kClient        *kubernetes.Clientset
	kDynamicClient *dynamic.DynamicClient
	EventRecorder  record.EventRecorder

	scaleLocks sync.Map

	scaleClient scale.ScalesGetter
	restMapper  *restmapper.DeferredDiscoveryRESTMapper

	logger         *zap.Logger
	watchNamespace string
}
```
The `ScaleHandler` is responsible for orchestrating scaling operations. It uses Kubernetes clients (`kClient`, `kDynamicClient`, `scaleClient`) to interact with the Kubernetes API for managing resources. It also incorporates an `EventRecorder` for reporting events, `scaleLocks` to prevent concurrent scaling operations on the same resource, a `restMapper` for discovering Kubernetes API resources, a `logger` for logging events, and `watchNamespace` to specify the namespace it monitors. This component acts as the central point for managing scaling decisions and actions.

### `prometheusMetadata`
```go
type prometheusMetadata struct {
	ServerAddress string            `json:"serverAddress"`
	Query         string            `json:"query"`
	Threshold     float64           `json:"threshold,string"`
	UptimeFilter  string            `json:"uptimeFilter"`
	Headers       map[string]string `json:"headers"`
}
```
The `prometheusMetadata` struct defines the configuration parameters required for a Prometheus-based scaler. It includes the `ServerAddress` of the Prometheus instance, the `Query` to be executed, a `Threshold` value that triggers scaling actions, an `UptimeFilter` to refine the query, and `Headers` for authentication or other HTTP-related needs. This metadata is crucial for configuring how the `prometheusScaler` interacts with Prometheus.

### `prometheusScaler`
```go
type prometheusScaler struct {
	httpClient           *http.Client
	metadata             *prometheusMetadata
	cooldownPeriod       time.Duration
	defaultServerAddress string
	defaultHeaders       map[string]string
}
```
The `prometheusScaler` is an implementation of the `Scaler` interface specifically designed for scaling based on metrics from Prometheus. It holds an `httpClient` to communicate with the Prometheus server, `metadata` containing the Prometheus-specific configuration, a `cooldownPeriod` to prevent rapid, successive scaling actions, and default values for the Prometheus server address and HTTP headers. This component translates Prometheus metrics into scaling decisions, enabling dynamic adjustments of service replicas.