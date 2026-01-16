# operator_internal_controller Module Documentation

## Introduction

The `operator_internal_controller` module is a core component within the operator, responsible for orchestrating the reconciliation and management of `ElastiService` custom resources. It acts as the central control plane, ensuring that the desired state of `ElastiService` objects, as defined by users, is consistently maintained in the Kubernetes cluster. This module interacts with various other operator components, including API definitions, informers, and scaling handlers, to provide a robust and responsive control loop.

## Architecture Overview

The `operator_internal_controller` module integrates with several other modules to perform its reconciliation tasks. It primarily consists of the `ElastiServiceReconciler`, which is responsible for the main control loop, and helper components like `opsInformer` which process object updates.

```mermaid
graph TD
    subgraph operator_internal_controller
        controller[operator_internal_controller]
        reconciler[ElastiServiceReconciler]
        ops_informer[opsInformer]
    end

    controller --> reconciler
    controller --> ops_informer

    reconciler --> api_types[operator_api_v1alpha1]
    reconciler --> informer_manager[operator_internal_informer]
    reconciler --> scale_handler[pkg_scaling]
    
    click reconciler "elastiservice_controller.md" "View ElastiServiceReconciler Documentation"
    click ops_informer "ops_informer.md" "View opsInformer Documentation"
    click api_types "operator_api_v1alpha1.md" "View operator_api_v1alpha1 Module Documentation"
    click informer_manager "operator_internal_informer.md" "View operator_internal_informer Module Documentation"
    click scale_handler "pkg.md" "View pkg Module Documentation"
```

## High-Level Functionality

The `operator_internal_controller` module provides the following high-level functionalities:

*   **`ElastiServiceReconciler`**: This is the heart of the controller, implementing the Kubernetes reconciliation loop for `ElastiService` resources. It observes changes to `ElastiService` objects and takes appropriate actions to align the cluster state with the desired state defined in the CRD. This includes managing associated deployments, services, and other Kubernetes resources, as well as interacting with the scaling logic.
*   **`opsInformer`**: This component handles updates related to Kubernetes objects, providing the `ElastiServiceReconciler` with the necessary information to make informed decisions during the reconciliation process. It specifically uses the `updateObjInfo` struct to encapsulate relevant object details for processing.

For detailed information on the `ElastiService` custom resource definition, refer to the [operator_api_v1alpha1.md](operator_api_v1alpha1.md) documentation.
For details on how informers work and their management, see the [operator_internal_informer.md](operator_internal_informer.md) documentation.
For information regarding the scaling mechanisms, refer to the [pkg.md](pkg.md) documentation.
