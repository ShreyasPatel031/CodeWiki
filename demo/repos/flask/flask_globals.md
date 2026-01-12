# flask_globals Module Documentation

## Introduction

The `flask_globals` module provides thread-local proxy objects for accessing application context, Flask application, request, session, and application globals. These proxies are essential for accessing context-dependent information within Flask applications without explicitly passing around context objects.

## Architecture

The `flask_globals` module defines several proxy classes that inherit from `ProxyMixin`. These proxy classes provide access to the current application context, Flask app, request, session, and application globals. The core component is the `ProxyMixin` which is responsible for deferring operations to the underlying object.

```mermaid
classDiagram
    class ProxyMixin~T~ {
        _get_current_object() : T
    }
    class AppContextProxy
    class FlaskProxy
    class RequestProxy
    class SessionMixinProxy
    class _AppCtxGlobalsProxy

    ProxyMixin <|-- AppContextProxy
    ProxyMixin <|-- FlaskProxy
    ProxyMixin <|-- RequestProxy
    ProxyMixin <|-- SessionMixinProxy
    ProxyMixin <|-- _AppCtxGlobalsProxy

    AppContextProxy -- AppContext: Accesses
    FlaskProxy -- Flask: Accesses
    RequestProxy -- Request: Accesses
    SessionMixinProxy -- SessionMixin: Accesses
    _AppCtxGlobalsProxy -- _AppCtxGlobals: Accesses

   
   class AppContext [[flask_ctx.md#AppContext]]
    link Flask [[flask_app.md#Flask]]
       class SessionMixin [[flask_sessions.md#SessionMixin]]
                link Flask [[flask_app.md#Flask]]

    AppContext : Defined in [flask_ctx.md#AppContext]
    Flask : Defined in [flask_app.md#Flask]
    Request : Defined in [flask_wrappers.md#Request]
    SessionMixin : Defined in [flask_sessions.md#SessionMixin]
    _AppCtxGlobals : Defined in [flask_ctx.md#_AppCtxGlobals]



```

## Core Components

### ProxyMixin

`ProxyMixin` is a base class for creating proxy objects. It provides the `_get_current_object` method, which is responsible for resolving the actual object being proxied. It is an abstract class.

### FlaskProxy

`FlaskProxy` is a proxy for the Flask application instance. It inherits from `ProxyMixin` and provides access to the current Flask application.

### AppContextProxy

`AppContextProxy` is a proxy for the application context. It inherits from `ProxyMixin` and provides access to the current application context. See [flask_ctx.md#AppContext] for more details on `AppContext`.

### RequestProxy

`RequestProxy` is a proxy for the request object. It inherits from `ProxyMixin` and provides access to the current request object. See [flask_wrappers.md#Request] for more details on `Request`.

### SessionMixinProxy

`SessionMixinProxy` is a proxy for the session object. It inherits from `ProxyMixin` and provides access to the current session object. See [flask_sessions.md#SessionMixin] for more details on `SessionMixin`.

### _AppCtxGlobalsProxy

`_AppCtxGlobalsProxy` is a proxy for the application context globals. It inherits from `ProxyMixin` and provides access to the current application context globals. See [flask_ctx.md#_AppCtxGlobals] for more details on `_AppCtxGlobals`.

## Relationships to Other Modules

- **flask_app**: `FlaskProxy` provides access to the `Flask` application object.
- **flask_ctx**: `AppContextProxy` provides access to the `AppContext` and `_AppCtxGlobals`.
- **flask_wrappers**: `RequestProxy` provides access to the `Request` object.
- **flask_sessions**: `SessionMixinProxy` provides access to the `SessionMixin`.

## Usage

The proxy objects in `flask_globals` are typically used within Flask views, templates, and other parts of the application where access to the application context, request, or session is needed. They are automatically managed by Flask and should not be instantiated directly.
