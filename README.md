# Branching Realms - Backend Architecture & Data Pipeline

## Overview
Branching Realms is a released, production-level mobile interactive fiction(CYOA) platform. This repository details the backend infrastructure and the custom Python automation scripts engineered to manage the application's data pipeline.

## Backend Infrastructure
The application relies on a cloud-based NoSQL architecture to handle dynamic user paths and data storage:
* **Firebase Firestore:** Utilized as the primary database to store, retrieve, and manage complex, branching story nodes and state data in real-time.
* **Firebase Authentication:** Integrated for secure user login and session management.
* **Firebase Analytics:** Implemented to track user retention, path selection, and application performance metrics.

## Python Automation Scripts
To eliminate the bottleneck of manually entering hundreds of text nodes into the Firestore database, I built two distinct Python utility programs to automate the deployment pipeline:

1. **The Data Parser:** A Python script designed to programmatically scan raw writing assets, format the text, and structure it into a clean JSON/dictionary format ready for database insertion.
2. **The Batch Uploader:** A Python-based automation tool utilizing the Firebase Admin SDK to connect to the live Firestore database and execute batch uploads, instantly populating the application's live environment with zero manual data entry.

## Core Technologies
* **Languages:** Python, Kotlin (Front-end context)
* **Databases/APIs:** Firebase, Cloud Firestore, NoSQL Data Structures
* **Methodology:** Automated Data Pipelines, API Integration

---

*Note: The front-end source code and proprietary story data for the Branching Realms application are withheld to protect commercial intellectual property. The Python utility scripts are highlighted here to demonstrate backend automation capabilities.*
