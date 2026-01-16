# Messages Module Documentation

## Purpose
The `messages` module defines the data structures and formats used for inter-module communication within the system. It ensures a consistent and well-defined way for different components, particularly the operator and resolver, to exchange information regarding host details and request counts.

## Core Components

### `Host`
```go
type Host struct {
	IncomingHost   string
	Namespace      string
	SourceService  string
	TargetService  string
	SourceHost     string
	TargetHost     string
	TrafficAllowed bool
}
```
The `Host` struct represents detailed information about a network host and its traffic routing. It includes:
- `IncomingHost`: The hostname as received.
- `Namespace`: The Kubernetes namespace of the related services.
- `SourceService`: The name of the service initiating the traffic.
- `TargetService`: The name of the service intended to receive the traffic.
- `SourceHost`: The actual host from which the traffic originates.
- `TargetHost`: The actual host to which the traffic is directed.
- `TrafficAllowed`: A boolean flag indicating whether traffic is permitted for this host configuration.

This struct is crucial for routing decisions and understanding the flow of requests between services.

### `RequestCount`
```go
type RequestCount struct {
	Count     int    `json:"count"`
	Svc       string `json:"svc"`
	Namespace string `json:"namespace"`
}
```
The `RequestCount` struct is used to convey information about the number of requests directed to a specific service. It contains:
- `Count`: An integer representing the total number of requests.
- `Svc`: The name of the service (`svc`) to which the requests are directed.
- `Namespace`: The Kubernetes namespace where the service (`svc`) resides.

This struct is vital for metrics collection and scaling decisions, allowing components like the operator to react to changes in service demand.