# Print Vault

Print Vault is a self-hosted application for managing your 3D printer inventory, parts, and projects.

## Installation

This guide will walk you through setting up Print Vault on a server using Docker and Docker Compose.

### Prerequisites

Before you begin, you will need a server (such as a Proxmox LXC container, a VPS, or a Raspberry Pi) with the following software installed:

- **Git**
  
- **Docker**
  
- **Docker Compose**
  

---

## Guide 1: Standard Installation (HTTP)

This method will get your Print Vault instance running and make it accessible on your local network.

### Step 1: Clone the Repository

Connect to your server's terminal (e.g., via SSH) and clone the Print Vault source code.

Bash

```
git clone https://github.com/your-username/print-vault.git
cd print-vault
```

### Step 2: Configure Your Environment

Print Vault is configured using a `.env` file. A template is provided to make this easy.

1. **Copy the Template:** Create your personal configuration file by copying the example.
  
  Bash
  
  ```
  cp .env.example .env
  ```
  
2. **Edit the `.env` File:** Open the new `.env` file with a text editor (like `nano .env`) and fill in your details.
  
  ```
  # Print Vault Environment Variables
  # This file contains sensitive information and should NOT be shared.
  
  # 1. Django Secret Key
  # Generate a new key here: https://djecrety.ir/
  DJANGO_SECRET_KEY='your-super-secret-key-goes-here'
  
  # 2. PostgreSQL Database Password
  # It's highly recommended to change this from the default.
  POSTGRES_PASSWORD='a-new-secure-password'
  
  # 3. Application Hostname/IP
  # This should be the IP address of your server.
  APP_HOST='192.168.1.100'
  
  # 4. Application Port
  # The external port the application will be accessible on.
  APP_PORT=8080
  ```
  

### Step 3: Create Data Directories

These folders will persistently store your application's database and your uploaded photos and files, keeping them safe even when the containers are updated.

Bash

```
mkdir -p ./data/postgres
mkdir -p ./data/media
```

### Step 4: Build and Run the Application

This single command will build the Docker images and start all the necessary services in the background.

Bash

```
docker compose up --build -d
```

The first time you run this, it may take several minutes to download the base images and build the application.

### Step 5: Access Print Vault

That's it! Your instance of Print Vault is now running. You can access it in your web browser by navigating to the IP address and port you configured in your `.env` file.

**Example:** `http://192.168.1.100:8080`

---

## Guide 2: Secure Remote Access with Tailscale (Optional)

This guide builds upon the standard installation and adds secure HTTPS access, allowing you to connect to your Print Vault from anywhere. This method also enables the PWA "Add to Home Screen" feature on mobile devices.

### Prerequisites

- Print Vault is already installed and running using the **Standard Installation** guide above.
  
- A [Tailscale](https://tailscale.com/) account (a free personal account is sufficient).
  
- The Tailscale client is installed and running on the same server as your Print Vault application.
  

### Configuration Steps

**1. Authenticate Your Server with Tailscale**

First, ensure the Tailscale client on your server is running and authenticated to your account.

Bash

```
# Start the client and enable the SSH server
tailscale up --ssh

# Follow the URL provided to log in and authorize the machine.
```

**2. Configure Tailscale Serve**

Run the following command on your server. This tells your Tailscale client to act as a secure reverse proxy for your Print Vault container.

- Replace `5173` with the `APP_PORT` you set in your `.env` file.
  
- The `--bg` flag runs the service in the background, so it will persist even if you disconnect your SSH session.
  

Bash

```
tailscale serve --bg http://127.0.0.1:5173
```

**3. Access Print Vault Securely**

Tailscale will now handle all the HTTPS and SSL certificate management for you. It will make your application available at a secure, private URL based on your server's Tailscale name.

The URL will look like this: `https://<your-server-name>.<your-tailnet>.ts.net`

You can now use this HTTPS address to access Print Vault from any device that is also logged into your Tailscale network.
