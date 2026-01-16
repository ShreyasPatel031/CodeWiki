# Config Module Documentation

## Purpose
The `config` module is responsible for defining and managing the configuration structures used throughout the system. It provides a centralized way to access various application settings and specific configurations for different components.

## Core Components

### `Config`
```go
type Config struct {
	Namespace      string
	DeploymentName string
	ServiceName    string
	Port           int32
}
```
The `Config` struct holds general application configuration parameters such as the Kubernetes `Namespace`, the `DeploymentName` of the application, the `ServiceName` associated with it, and the network `Port` it exposes. This provides a baseline for operational settings.

### `ResolverConfig`
```go
type ResolverConfig struct {
	Config

	ReverseProxyPort int32
}
```
The `ResolverConfig` struct extends the base `Config` struct and adds specific configuration relevant to the resolver component. Notably, it includes `ReverseProxyPort`, indicating the port on which the reverse proxy component of the resolver operates. This allows the resolver to have its own specialized configuration while inheriting common settings.
