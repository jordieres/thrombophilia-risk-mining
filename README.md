# Comprehensive Data Mining and Machine Learning Workflows for Thrombophilia Risk Stratification

This repository houses an advanced, object-oriented framework engineered to deconstruct hypercoagulable risk factors utilizing a consolidated national database for thrombophilic disease.

## Functional Architecture

The functional capabilities of the execution engine and its interaction with clinical research actors are described in the following specification:

![System Functional Use Cases](docs/architecture/UseCaseDiagram.png)

The entire dataset operations, extending from compressed Parquet tables to multi-stage statistical outputs, follow a highly decoupled execution path:

![System Architecture and Component Layout](docs/architecture/ComponentsDiagram.png)

## Detailed Technical Documentation

For a deep dive into the runtime sequence validation, class inheritance structures, state machine boundaries, and multi-node deployment topologies, please consult the comprehensive technical manual available at [Technical Reference Guide](docs/technical_reference.md).
