---
title: "FileFlow"
subtitle: "A Multi-User File Sharing Application"
author:
  - "Tanmoy Debnath — 121324683"
  - "Faruq Ayinla — 121404736"
date: "13/03/2026"
geometry: margin=1in
fontsize: 11pt
colorlinks: true
linkcolor: blue
urlcolor: blue
---

# FileFlow

## A Multi-User File Sharing Application

### Project Report

**Module:** CS3306  
**Team members:**  
- Tanmoy Debnath — 121324683 
- Faruq Ayinla — 121404736

**GitHub repository:** https://github.com/tanmoy03/file-transfer-system

**Academic honesty and integrity declaration**  
We declare that this report describes our own project work. Any external ideas, tools, or sources that influenced the project are acknowledged in the report. We understand that submitted work must accurately reflect the system we built and the contributions made by each team member.

# 1. Introduction

Our project is a multi user file sharing application named FileFlow. This system allows users to create an account and upload files. These files can be viewed, sent to another user, and received through an inbox like workflow. The final version of our project is delivered through a web interface, backed by a Python Flask and a SQLite database.

The initial idea was that we could "send a file from one person to another". Before coding, our main objective was to understand what basic needs are required from our file transfer system to make it both usable and practical in a real world setting.  How do users identify each other? How do we authenticate them? Where should files be stored? What happens when the server restarts? How should the user interface explain the difference between a file I uploaded and a file I received from someone else? These are just some of the questions that we had initally so that we could plan ahead and be prepared for what we needed to accomplish. 

At the outset, our project did not begin with a web application. The very first version was a socket based file transfer system developed in Python, with an focus on lower level networking. That version helped us understand message formats, acknowledgements, packet flow, and the practical difficulty of making two machines talk reliably. Later, we moved onto a central server web architecture that was easier to demonstrate and extend. This method aligned better with the requirement that multiple clients should be able to identify each other and exchange files without manually typing IP address. For our team, this was a major jump as we had previously just had a client server architecture with requirement for IP addresses. 

To summarize this report, we began with the problem and the motivation for building our file transfer system. We then discussed the limitations of obvious existing approaches; describe the overall architecture of FileFlow; and examine the main subsystem: authentication, file storage, transfer, and the user interface. To wrap up the report we examine the design decisions that we made, the challenges we faced along the way and lastly a contribution table that clarifies who worked on which parts.

# 2 The Problem and Why It Is Interesting

From an exterior viewpoint, one might ask "why build a file sharing system when many already exist?". The answer is that our project is not simply about transferring files. It is having a deeper undersanding a software system can scale when simple requirements are made concrete.

The initial problem statement sounds modest:

- let multiple users connect to one central server
- let each user upload and download files
- let users send files to each other
- avoid requiring the sender to know the receiver's IP addrss
- provide a user interface that makes the process clear

From this problem statement, we can view that each line hides a design choice. By allowing multiple users connect to one central server, this immediately raises concurrency and user identity concerns. The requirement of a central server denotes that the server is responsible for routing, storage, and control. The uploading and downloading of files indicates that there is both raw file data and metadata. To allow users to send files to each other, we had to model users as named entities instead of just anonymous connections.  Finally, we must provide a user interface so that the system can be understood by an ordinary person and not just by developers reading through terminal output. 

Through these design decisions we had a groundwork for our project and ultimately made the project sound feasible yet exciting. The project was small enough to implement in 8 weeks, but large enough to force us to think like system designers rather than only like programmers.

# 3. Existing Solutions and Why We Still Built Our Own

There are already numerous ways people share files.

Firstly, it can be done in a simple peer to peer file transfer over a direct network connection. This can work in small group experiments but it is extremely fragile as one machine must know the other IP address whcih isn't practical, and both sender and receiver are often on the same network for the receiver to be reachable. This is a useful excercise for understanding sockets but isn't a particularly friendly user experience. 

The second method that we mention is cloud storage. Popular services such as Google Drive, Dropbox, OneDrive, or WeTransfer solve most user facing problems already. They provide web interfaces, accounts, file storage, sharing links, and clean workflows. For a real consumer product, these services are more advanced and mature than anything we could build in 8 weeks. However, by using these services this would avoid the very architectural questions the project was supposed to explore. We wanted to design the server so that we could decide how users were represented and understand how file contents relate to one antother.

The third is a simple network file share, where all files are placed in one shared directory. This reduces transfer friction, but it creates a different problem: there is no clear ownership, no transfer action and weak support for an inbox like idea of "Faruq sent this to Tanmoy". This implementation also gives us very little practice building an application layer.

The motivation for building FileFlow was not to compete with services like OneDrive or Dropbox but instead the fact that we wanted to build a smaller, understandable system ourselves. We were especially interested in the gap between a networking prototype and a usable application. A direct socket program has the ability to send bytes. However for a real file sharing application it must also be able to manage users, sessions, persistence, and keep in line with user expectations.

# 4. From a Socket Prototype to a Web Application

The development of this project evolved in stages:

## 4.1 First prototype: sockets and UDP/TCP thinking

In the earliest version of the project we focused on a custom Python client and server.  We explored socket based communication and even considered UDP because it gave us room to think about acknowledgements and custom reliability. This phase taught us that low level networking is excellent for understanding what data transfer really means, but also that low level networking can dominate the project if left unchecked.

For example, direct socket communication made server and peer discovery awkward. Even on the same WiFi network, small issues such as firewall settings or VPN interference would consume significant time. That was essential to our understanding of socket based communication, but it also showed us that a file transfer system with multiple users would benefit from a more centralised design which in turn would make the system more controllable.

## 4.2 Architectural pivot: one server, many clients

The major architectural decision we made was to move from sender talking directly to receiver towards clients talk to a server, and the server manages the routing. This was where we made some major improvements to our project. 

Once we adapted to that model, several decisions became much easier:

- users could be identified by account names rather than network addresses
- the server could keep a record of uploads and transfers
- file transfer between users could be implemented as a server side operation
- the user interface no longer needed to expose unecessary networking details

## 4.3 Final direction: a web application

The final stage involved switching to a browser-based interface from our command line client. This was more than simply a visual makeover; it completely altered our system's design so that the average person could use it. Rather than attempting to construct the entire system around a unique application protocol, we divided the system into:

- a frontend responsible for interaction and feedback
- an HTTP API responsible for application logic
- a storage layer responsible for files and metadata

That separation allowed the system to be easier to maintain. It also made it easier to present to the lecturer and to future readers of the repository.

# 5. Architectural Overview

A first-year student could easily understand FileFlow's final architecture, yet still sufficient to support careful design.

## 5.1 High-level structure

```text
Browser (Frontend)
    |
    | HTTP requests
    v
Flask Backend API
    |
    | file metadata + user data
    v
SQLite Database
    |
    | file contents
    v
Per-user storage directories
```

Requests are sent to the backend by the browser. The backend saves file contents in per-user directories on disk, verifies permissions, reads or writes metadata from SQLite, and authenticates the user. The backend registers the new metadata entry and copies the file into the recipient's directory when a user transmits a file to another.

## 5.2 Why this architecture fits the problem

We gained four significant advantages from this architecture.

It first divided concerns. Forms, buttons, progress bars, layout, and status messages are all managed by the frontend. Trust-sensitive tasks, such as verifying tokens and determining whether a user is permitted to download or remove a file are handled by the backend. Data is stored in SQLite, and the actual file bytes are stored in the filesystem.

It also made the system easier to comprehend. Every component serves a distinct function. When debugging, this is important. If a file doesn't show up, it's most likely a metadata retrieval error rather than an upload widget bug. When a user receives a 401 error, session handling—rather than file storage—is the issue.

Thirdly, it enabled incremental development. Without changing the other layers, we could make one layer better. For instance, switching from in-memory information to SQLite persistence drastically altered the backend, while the frontend API contract remained largely unchanged.

Fourth, it matched the module's instructional objectives. Although the project does not rely on direct host-to-host socket connectivity, it does demonstrate networking through application architecture.

# 6. Main Components

# 6.1 Authentication and session management

One of the most significant advancements over the initial prototype was authentication. A user could essentially claim any username in earlier versions of the system. Demos were made possible by that, but it wasn't true security. A system that allowed users to register, log in, and obtain a session token was what we were looking for. 

Users are kept in a SQLite database on the backend. A hashed password and a distinct username are included in every entry. Instead of saving plaintext passwords, we made advantage of Werkzeug's password hashing tools. This is an essential lesson for our project: password management should adhere to the same general guidelines as larger systems, regardless of the system's size. 

The backend generates a random session token and saves it in an in-memory session dictionary upon a successful user login. The token is kept in `localStorage` by the browser. The token is included by the browser in a `Authorisation: Bearer ...` header for protected routes.

We were able to create a lightweight yet practical authentication model with this method. It also resulted in a repeating lesson: login is a protocol rather than merely a form. When we first implemented prompt-based browser login, the interface was clumsy and loops were introduced when a token expired and the frontend attempted to recover on its own. The entire process was made simpler by shifting authentication to a separate `auth.html` page. 

# 6.2 Persistent file metadata

File metadata was kept in a Python dictionary in an early backend version. This made it simple to create the initial upload/list/download sequence, but it had a major drawback: even if the files were still on disk, the metadata disappeared if the backend restarted.

This issue is an excellent representation of the importance of software architecture. The file upload itself was not the source of the fault. It resulted from a mismatch between two types of persistence. Because the contents of the files were written to disc, they were persistent. Because file metadata was only stored in memory, it was not permanent.

The fix was to create a `files` table in SQLite. Each row stores:

- a unique file id
- the original filename
- file size
- upload timestamp
- owner username
- saved path on disk

The file list became durable after the modification. The user's view of their files was no longer erased by a server restart. This was one of the project's most significant architectural advancements since it transformed the system from a demo that only functioned when running into an application whose state endured restarts.

# 6.3 Per-user storage directories

Actual file contents are kept by the system in directories under `web/api_storage/`, one directory per user. The backend saves any files Tanmoy uploads under `api_storage/tanmoy/`. The simplicity of this design was deliberate. It made ownership obvious both theoretically and physically, avoiding the need for a sizable shared directory.

The directory structure is not itself the source of truth but SQLite is. However, the directory structure reinforces the ownership model and makes manual inspection of the system easier during debugging.

The combination of a database row and a saved path on disk turned out to be a strong pattern:

- the database answers "what files belong to this user?"
- the filesystem answers "where are the bytes?"

# 6.4 Upload workflow

The browser is where the upload path starts. Files can be selected using a file picker or dragged and dropped onto the interface. It employs XMLHttp, queues uploads, and verifies file types and sizes. While monitoring progress, it transmits `multipart/form-data` to the backend using the request command.

One might ask why not use the more straightforward `fetch()` API instead of `XMLHttpRequest`? This is because the implementation of progress events for this project was made simpler using `XMLHttpRequest`. This enabled us to display user states like queued, uploading, successful, unsuccessful, cancelled, and retry.

The backend verifies authentication, stores the file in the user's directory, adds a metadata record to SQLite, and generates a JSON response on the server side. The file list is then updated by the frontend.

Even though upload looks like a narrow feature, it touches nearly every layer of the system:

- the frontend must collect and validate the file
- the HTTP layer must carry the bytes
- the backend must enforce authentication
- storage must write the file
- the database must record the metadata
- the UI must update to reflect the new state

# 6.5 Download and delete

From the user's point of view, download and delete appear simple, however they exposed a number of minor problems.

The easier of the two is delete. The backend retrieves the file by id, verifies that the user making the request is the owner, deletes the metadata row from SQLite, and destroys the physical file if it is present.

The download was more engaging. The browser requested a straightforward button or link that could be clicked. However, the API's normal authentication mechanism used an `Authorization` header, which is easy to send with JavaScript requests but not with a plain browser navigation to a new tab. For this project, we decided to support token-in-query download URLs. Put otherwise, a URL such as `/files/<id>/download?token=...` might be opened by the browser. For a project like ours, it resolved an actual integration issue and enabled us to freely discuss the trade-off, but it is not a production grade design for a public internet application.

# 6.6 Sending files between users

Beyond simple storage, the ability to transfer files between users is the most crucial program function.

This feature can be viewed in at least two ways.

The first is to think of a file as moving: ownership changes when Tanmoy sends the file to Faruq. The second is to picture a file being delivered: Faruq gets a copy, and Tanmoy keeps his file. The second model was our choice.

Technically, the send operation works as follows:

1. the frontend asks the server to send file `<id>` to a recipient username;
2. the backend confirms that the sender owns the source file;
3. the backend confirms that the recipient exists;
4. the backend copies the physical file into the recipient's directory;
5. the backend inserts a new metadata record owned by the recipient.

This model is simple and robust. It avoids permission confusion and gives the receiver an independent file record and also maps well onto the inbox concept we added later.

# 6.7 Inbox / received files view

Another usability issue emerged when users could transfer files to one another. The recipient will no longer be able to quickly identify which files were uploaded by them and which were received from someone else if all files just show up in one list.

The inbox function resulted from this. From a conceptual standpoint, the inbox is a separate or filtered view of files that have been received. The user is presented with a similar interface concept from chat and email systems: "these are the files that came to me." The project was enhanced in two ways by this feature.

It first improved the clarity of the user experience. File transfer was no longer a hidden side effect but rather an obvious workflow.

Second, by making us consider file origin directly, it enhanced the design. A file has a narrative in addition to its name and path. It was uploaded by who exactly? Who got it? Are they concepts the same? We were able to make it clear that sending and receiving are high level system actions thanks to the inbox functionality.

# 6.8 Online users

Technically speaking, the online users panel was a minor innovation, but it gave the application a much more complete feel.

A user with an active session token is regarded as "online" by the backend. When the sender selects a recipient, the frontend uses the list of users who are currently online.

User friction was decreased by this feature. The application can display who is available right now rather than requiring the sender to recall every username that exists. Better demos were also made possible by the list's ability to quickly highlight the system's multi-user nature.

# 7. Important Design Decisions

A trail of design choices is left by every unforeseen task. While some are intentional, others are found as a result of bugs. The following choices were especially crucial: 

## 7.1 Transfer via server rather than peer-to-peer

This was the project's main choice. It eliminated the requirement for users to know each other's network addresses, simplified networking, and allowed for the addition of ownership, authentication, and an inbox model.

The server takes on greater responsibility as a trade-off. It is now the authoritative owner of the file state rather than just a relay.

## 7.2 Web frontend instead of CLI-only interface

Although the web frontend made the system much simpler to use and display, the command-line interface was helpful for early research. Additionally, it made us consider states, error messages, and action clarity more carefully.

The drawback is that browser-based apps have limitations of their own, particularly with regard to downloads and authentication.

## 7.3 SQLite for persistence

Because SQLite offered true persistence without adding the setup stress of a larger database server, it was an ideal choice for this project. Additionally, it maintained the project's independence, which is important in an academic setting where the program needs to run on several student laptops.

## 7.4 Separate authentication page

Initially, we used prompts on the home page to handle authentication. It soon proved difficult to justify that strategy. Both the frontend logic and the user experience were made simpler by a dedicated authentication page. Now, the main page's sole purpose is to show the application. Whereas establishing the session is main feature of the auth page.

## 7.5 Token in query string for downloads

This was a practical design decision to enable browser downloads without completely modifying the authentication process. We acknowledge that in a production system, signed or expired sharing links would be a superior design. Nevertheless, the choice was appropriate for our project since it made the feature demonstrable and decreased friction.

# 8. Challenges and What We Learned

## 8.1 State is harder than it looks

File transfer appears to be about transferring data at first glance. In practice, managing the state contributed to a significant portion of the project. Who is signed in? Which user owns which files? Which data is stored on disk and which is stored in memory? When the server restarts, what should happen?

A major lesson here was that software bugs often come from inconsistent state boundaries rather than from incorrect syntax.

## 8.2 User experience changes architecture

A number of architectural modifications were brought about by frontend discomfort rather than backend accuracy. An excellent example is the separate auth page. Although it was awkward, the original logic could be made to work. The architecture had to change once we wanted the program to function like a typical web application.

We learned from this that utility is not aesthetic. Internal design can be reshaped by user-facing design.

## 8.3 Persistence should be designed early

Once we had a functional upload path, we switched from in-memory metadata to SQLite. In retrospect, persistence should have been given top priority sooner. Although the penalty of delaying persistence was repeated rework, the project still benefited from the staged approach because the simpler version made the more complex version easier to grasp.

## 8.4 Small features have hidden complexity

The inbox, logout, and online users list all appeared to be minor additions. Each of them actually traversed several levels. For instance, a logout button is more than just a button. It affects redirect logic, token storage in the browser, session invalidation, and the application's overall mental model.

One of the project's most obvious lessons was that "small feature" in software frequently translates to "small interface, large consequences."

# 9. Use of Generative AI Tools

We used generative AI tools during the project as assistants, not as independent developers. In practice this meant using them for the following tasks:

- brainstorming alternative designs
- explaining error messages and debugging ideas
- generating starter code snippets for Flask and JavaScript patterns
- suggesting UI wording and README phrasing
- helping organise architecture documentation

Every generated suggestion had to be reviewed, adapted, and tested by us inside the project itself. We frequently found that a generated answer was useful as a starting point but still needed changes to fit our codebase, our API design, or the actual behaviour of the application. This was especially true when integrating authentication, persistence, and frontend state.

Therefore, rather than taking the place of design labour, we see AI technologies as accelerators for iteration. We performed the final verification, debugging, integration, and architectural decisions, not AI.

# 10 Conclusion

FileFlow began as a networking problem we needed to solve to allow communication between multiple users for file transfer, but gradually grew into a full fledged application. Along the way, we transitioned from a single file list to a system that can handle upload, transfer, ownership, and receiving; from direct socket thinking to a server-centered web architecture; and from in-memory metadata to database persistence.

The fact that every feature now has a distinct place in the overall architecture, in addition to the project's functionality, is what makes it enjoyable. SQLite maintains the state, the filesystem saves the bytes, the frontend describes the workflow, and the backend enforces the rules. None of those parts is especially unusual on its own; the interesting part is how they fit together.

For a first year student that may be reading this report, we hope that the main takeaway of our project is that software architecture is not an abstract subject reserved strictly for large corporations. Even a small scale file sharing application benefits greatly from clear decisions  about boundaries, persistence and user experience. Those decisions are what turned our code into a system.

# Team Contribution Table

The brief asks for a clear statement of who did what. Because this is a two person project, our contribution table is shorter than it would be for a larger team, but it still aims to be specific.

| Team Member | Main Responsibility Areas | Detailed Contributions |
|---|---|---|
| **Tanmoy Debnath** | Networking, backend/server logic, authentication, persistence, system integration, documentation | Set up the initial project repository and core structure. Implemented the early TCP prototype and then led the transition to a UDP-based file transfer model with packet handling, acknowledgements, binary file transfer, server discovery, inbox retrieval, file deletion after download, user presence notifications, and progress feedback. Later led the move from the legacy socket prototype to the central multi-client server architecture. Implemented the multi-client TCP server, user login/logout handling, per-user storage, file sending between users, online user tracking, SQLite-backed user authentication, persistent file metadata storage, separate authentication routing, server-side file transfer fixes, project naming, and the main README/documentation updates. Also carried out backend testing, cleanup, and final integration of frontend and backend components. |
| **Faruq Ayinla** | Frontend/UI design, browser interaction flow, usability improvements, inbox presentation, frontend testing | Contributed to early project planning and role discussion. Helped develop the first browser-based interface using Flask templates for listing users, sending files, and inbox download. Later implemented the fuller web frontend with file upload, progress bar, file list display, download, delete, and share-link copy. Worked on improving the structure and usability of the application so that it could be demonstrated as a complete web-based file sharing system rather than only a networking prototype. Added the inbox view and separated uploaded files from received files to make file sharing clearer for users. Also contributed to frontend testing, UI refinement, and the final demonstration flow. |

## Contribution Timeline Summary

### Tanmoy Debnath
- **Weeks 1–2:** Helped define the project idea, created the repository skeleton, and took responsibility for client-server communication.
- **Weeks 3–5:** Built the initial TCP file transfer version, then switched to UDP and implemented structured packets, stop-and-wait reliability, discovery, binary chunk transfer, and inbox handling.
- **Week 6:** Reworked the system into a central multi-client server architecture using TCP, including login, file forwarding, offline inbox support, real-time presence notifications, and progress tracking.
- **Weeks 7–8:** Led backend evolution into the final web-based system by implementing authentication, per-user storage, file transfer between users, online user tracking, logout/session handling, SQLite-backed persistence, separate authentication routing, and final documentation/branding updates.

### Faruq Ayinla
- **Weeks 1–2:** Contributed to brainstorming, planning, and role discussion.
- **Weeks 3–5:** Explored TCP file transfer locally, then contributed to the move toward UDP and testing across devices, including debugging communication issues and validating file transfer reliability.
- **Week 6:** Began frontend development for the new architecture by creating an early Flask-based web UI for listing users, sending files, and inbox download.
- **Week 7:** Implemented the fuller browser UI with upload, progress bar, file list, download, delete, and share-link functionality.
- **Week 8:** Added inbox presentation improvements and split uploaded files from received files, helping make the final system clearer and more usable for testing and demonstration.

## Overall Team Split

- **Tanmoy Debnath:** Core networking, backend architecture, authentication, storage, integration, and documentation.
- **Faruq Ayinla:** Frontend development, browser-based workflow, inbox UI, and user-facing improvements.