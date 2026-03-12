# FileFlow - Multi-User File Transfer System

## Overview

This project is a secure multi-user file transfer system that allows
users to upload, store, and share files through a central server.

Multiple users can connect simultaneously and send files to each other
without needing to know IP addresses.

The system was originally implemented using Python socket programming,
and later extended with a web-based frontend and HTTP API backend for
improved usability.

------------------------------------------------------------------------

## System Architecture

Browser (Frontend) 
    │ 
    │ HTTP Requests 
    ▼ 
  Flask Backend Server 
    │ 
    │ File Storage 
    ▼ 
  api_storage/ 
        ├── tom/ 
        ├── ethan/ 
        └── other_users/

------------------------------------------------------------------------

## Features

### User Authentication

Users log in with a username and receive a session token used to
authenticate API requests.

Endpoint: POST /login

------------------------------------------------------------------------

### File Upload

Users can upload files using: 
- File picker 
- Drag and drop

Features include: 
- File validation 
- Upload progress bar 
- Retry / cancel upload

Endpoint: POST /files

------------------------------------------------------------------------

### File Listing

Users can view their uploaded files including: 
- Filename 
- File size 
- Upload timestamp

Endpoint: GET /files

------------------------------------------------------------------------

### File Download

Files can be downloaded directly or through generated share links.

Endpoint: GET /files/{id}/download

------------------------------------------------------------------------

### File Deletion

Users can delete their uploaded files.

Endpoint: DELETE /files/{id}

------------------------------------------------------------------------

### File Transfer Between Users

Workflow:

1. Alice uploads file
2. Server stores file
3. Alice sends file → Bob
4. Server copies file
5. Bob sees file in his file list

Endpoint: POST /files/{id}/send

------------------------------------------------------------------------

### Online Users

The system tracks active users currently logged in.

Endpoint: GET /users/online

------------------------------------------------------------------------

### Logout / Session Management

Users can log out, which invalidates their authentication token.

Endpoint: POST /logout

------------------------------------------------------------------------

## Technologies Used

Backend -> Python - Flask

Frontend -> HTML - CSS - JavaScript

Version Control -> Git - GitHub

------------------------------------------------------------------------

## How to Run the Project

### 1. Install dependencies

pip install flask

------------------------------------------------------------------------

### 2. Start the backend server

python -m web.app

Server runs on: http://127.0.0.1:8000

------------------------------------------------------------------------

### 3. Open the frontend

Open in another terminal:

cd ui
python -m http.server 5173

------------------------------------------------------------------------

### 4. Login

Enter a username such as:

tom\ethan

------------------------------------------------------------------------

### 5. Upload and share files

Users can: 
- Upload files 
- View files 
- Send files to other users 
- Download files 
- Delete files

------------------------------------------------------------------------

## Future Improvements

Possible extensions include: 
- End-to-end encryption 
- File activity logging 
- Expiring share links 
- User storage limits 
- Real-time user presence updates
 
------------------------------------------------------------------------

## Legacy Implementation

The earliest implementation using UDP socket file transfer is stored in:

legacy_udp/

Another early implementation using TCP socket file transfer is stored in:

legacy_socket/

Version 1 (UDP) demonstrates: - Client-server socket communication - UDP
packet transfer - File transfer reliability

Version 2 (TCP) demonstrates: - Client-server socket communication through UDP discovery - TCP file transfer - Web API 

------------------------------------------------------------------------

## Authors

Team Members: Tanmoy Debnath, Tobi Ayinla

Team members contributed to: - Network communication - Backend server
development - Frontend interface design - System testing and debugging

------------------------------------------------------------------------
