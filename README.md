# IBABI Platform - Digital Agricultural Management System

![IBABI Platform]

## Overview

IBABI Platform is a comprehensive digital agricultural management system designed to revolutionize farming support in Rwanda. The platform connects government agricultural officers, farmers (citizens), and agricultural experts through a unified web application, PWA mobile app, and future USSD integration.

This system enables farmers to request resources, report issues, submit concerns, and make production reports while allowing officials at various administrative levels to manage inventories, approve requests, and provide timely feedback, creating a seamless agricultural support ecosystem.

## Key Features

### 🌾 For Farmers (Citizens)
- **User Registration & Profile Management**: OTP-based signup and login. Register lands and livestock for personalized services.
- **Resource Requests**: Request seeds, fertilizers, medicines, and other farming inputs.
- **Issue Reporting**: Report problems related to crops, livestock, or land directly from the field.
- **Production Reporting**: Log and submit reports on yields and livestock production.
- **Multi-channel Notifications**: Receive SMS and email updates on request status, issue resolutions, and important announcements.

### 🏛️ For Government Officials (Cell, District, National Levels)
- **Hierarchical Admin Management**: Super-admins can create lower-level officials (District -> Cell).
- **Inventory Management**: Track and manage agricultural resource stocks at various administrative levels.
- **Request & Issue Approval Workflow**: Review, approve, or deny farmer submissions with actionable feedback.
- **Dashboard & Analytics**: View maps and reports on resource distribution, common issue types, and regional hotspots.

### 🔧 For Agricultural Technicians
- **Assigned Task Management**: Receive and address technical issues escalated by cell or district officers.
- **Expert Feedback System**: Provide specialized advice and solutions to farmer-reported problems.

### 🤖 Platform-Wide Features
- **Advanced Authentication**: Secure JWT-based access with OTP login and password reset functionality.
- **Multi-language Support**: Interface available in multiple languages (e.g., Kinyarwanda, English, French).
- **Theme Support**: Switch between light and dark modes for user comfort.
- **AI-Powered Tools**:
  - **Yield Prediction**: AI models to predict crop yields based on historical and current data.
  - **Chatbot Assistant**: An interactive AI chatbot to answer common farmer queries and guide them.
- **Asynchronous Notifications**: Powered by Celery and Redis for reliable, real-time messaging via SMS and email.
- **Progressive Web App (PWA)**: Full mobile app functionality on iOS and Android without an app store.
- **Future USSD Integration**: Plan for accessibility via basic feature phones.

## Technology Stack

### Frontend
- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript
- **UI Library**: React with Shadcn/UI or similar component library
- **State Management**: React Query / TanStack Query & Zustand
- **Charting**: Chart.js
- **PWA**: Next-PWA

### Backend
- **Framework**: Django  & Django REST Framework (DRF)
- **Language**: Python 
- **Database**: PostgreSQL (Production),
- **Authentication**: Simple JWT with custom OTP handling
- **Async Task Queue**: Celery with Redis as the Broker/Result Backend
- **Caching**: Redis
- **Object Storage**:  AWS S3  for media files

### Deployment & DevOps
- **Web Server**: Nginx
- **WSGI Server**: Gunicorn
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions 
- **Platform**: PaaS (Render)

## System Architecture & User Roles

The platform operates on a hierarchical model based on Rwanda's administrative structure:

1.  **Super Admin (National Level)**
    - Has system-wide oversight.
    - Creates and manages District Officer accounts.
    - Views national-level analytics and reports.
    - Configures system-wide settings.

2.  **District Officer**
    - Created by the Super Admin.
    - Creates and Manages Cell Officers within their district.
    - Oversees district-level inventory, requests, and issues.
    - Views district-level dashboards.

3.  **Cell Officer**
    - Created by a District Officer.
    - First point of contact for farmers in their cell.
    - Validates and triages farmer requests and reports.
    - Manages cell-level inventory.

4.  **Agricultural Technician**
    - assigned to specific districts or cells.
    - Receives and resolves technical issues escalated by officers.
    - Provides expert advice and solutions.

5.  **Farmer (Citizen)**
    - Self-registers on the platform via OTP.
    - Can register multiple plots of land and livestock.
    - Submits requests and reports visible to their local Cell Officer.

## Deployed links**
  - https://ibabi.vercel.app/  

## SUPER ADMIN LOGIN CREDENTIALS
  - **EMAIL**: fidelensanze100@example.com
  - **PASSWORD** : Citizen123!
  - **OTP**: reach out to us at +250786161794, or **email**: fidelensanzumuhire9@gmail.com so that we can give you the OTP after successfully logging in with email and password

## You can create as many citizen users as you want,and logging in as well. 

## Creading admin users( district officer, cell officer, teachnicians must be followed as the rules we stated describes. see the info above for more clarities and how those users can be created as well.)


## TEAM MEMBERS:
 - Fidele Nsanzumuhire  ----> Full stack engineer(Group leader)
 - Nsengiyumva Augustin -----> AI engineeer
 - Niyoyita Stephane --------> Data analyst
 - Bizimana Ibrahim  ---------> AI engineer
 - Giraneza Fiston  -----------> UX/UI Engineer

