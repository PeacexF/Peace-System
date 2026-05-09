# Real-Time Monitoring System

Peace-System is a lightweight open-source observability platform for local system monitoring. (runs on and utilizes localhost)

A hybrid Go + Python monitoring stack with:
- realtime metrics collection;
- event-driven processing pipeline;
- anomaly detection;
- live dashboard;
- historical metrics storage.
- logging

Inspired by tools like Netdata and Datadog, but designed for local/self-hosted usage.

---

# Features

## Metrics Collection
- CPU monitoring
- RAM monitoring
- Disk usage monitoring
- Network monitoring
- Docker/container metrics

## Event-Driven Architecture
- Internal event pipeline
- Pub/Sub routing system
- Typed event models
- Async processing

## Analytics & Alerting
- Threshold-based alerts
- Sliding window analysis
- Suspicious activity detection
- Realtime notifications

## Dashboard
- Live metrics graphs
- WebSocket-powered updates
- Historical metrics view
- Alert panel
- System logs

## Storage
- SQLite-based storage
- Historical time-series metrics
- Alert history
- Event persistence

## Highly configurable
- CPU metrics
- RAM metrics
- UDP port
- Storage
- Web port
- Collection Intervals
- Alert logic
All of the above can be configured in the `settings/config.json` file

---

# Architecture

``` plaintext
[ Go Collectors ]
    └── goroutines:
        CPU
        RAM
        Disk
        Network
        Docker
        (package collectors)

      ↓ UDP localhost


[ Python Event Pipeline ]
    ├── Validation
    ├── Normalization
    ├── Routing
    ├── Logging
    ├── Storage
    ├── Analyzer
    ├── Alert Engine
    ├── WebSocket Gateway
    └── REST API (FastAPI)

         ↓

[ React Dashboard ]
```

---

# Tech Stack

### Backend
Go — system collectors  
Python — pipeline, analytics, API  
FastAPI — REST API + WebSocket  
SQLite — metrics storage  
Pydantic — typed event models

### Frontend
React  
Vite  
TailwindCSS  
Recharts  


## Goals
- Lightweight
- Self-hosted
- Modular
- Realtime
- Easy to extend
- Open-source
- Portfolio-quality architecture (pls hire me)

## Security Notes

This project is designed for local/self-hosted usage.

- No cloud telemetry
- No external data collection
- Localhost-only communication
- Configurable ports/settings

## For contributors
I do look forward to work with someone, ideally a frontend dev that knows **React** and wants to have a cool project for his portfolio or just wants to create and contribute.

# License

MIT License  

## Important Note
I do not consent to the usage of Go collectors in malicious intents, such as creating a monitoring system for mining malware/spyware or any other istance where they would be included in malware of any kind.  
This project should only be used in the purpose of detecting such malware, education and learning, not creating / improving malware's logic.