# Gigawatt Data Center - Energy Analysis

>[!TIP]
>To report bugs, please create an issue.

An analysis tool for powering data centers with solar, wind and gas.

## Commercial Usage
For commercial usage requests, you can fill out this form [here](https://forms.gle/rp3yCUztKdKW2Gcx8).

## Getting Started

You can check out the site at [gigawatt-datacenter.com](https://gigawatt-datacenter.com) OR run it locally with.

```
pip install uv
uv venv
```
then
```
uv pip install -r requirements.txt
```
then
```
cd app
python app.py
```
## Acknowledgements

Inspired by a blog from [Austin Vernon](https://austinvernon.site/blog/datacenterpv.html).

## Remote Server Notes

### Setting Up Systemd Service

To manage the Gradio app as a systemd service, follow these steps:

1. Create a new user for running the app:
   ```
   sudo adduser gigawatt-datacenter
   ```

2. Change ownership of the project directory:
   ```
   sudo chown -R gigawatt-datacenter:gigawatt-datacenter /var/www/gigawatt-datacenter
   ```

3. Create a systemd service file:
   ```
   sudo nano /etc/systemd/system/gigawatt-datacenter.service
   ```

4. Add the following content to the file:
   ```ini
   [Unit]
   Description=Gigawatt Data Center Gradio App
   After=network.target

   [Service]
   User=gigawatt-datacenter
   WorkingDirectory=/var/www/gigawatt-datacenter
   ExecStart=/var/www/gigawatt-datacenter/.venv/bin/python /var/www/gigawatt-datacenter/app/app.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

5. Save and close the file (in nano: Ctrl + X, then Y, then Enter).

6. Reload the systemd daemon:
   ```
   sudo systemctl daemon-reload
   ```

7. Enable the service to start on boot:
   ```
   sudo systemctl enable gigawatt-datacenter.service
   ```

8. Start the service:
   ```
   sudo systemctl start gigawatt-datacenter.service
   ```

### Managing the Application Service

Use these commands to manage the Eire Data Gradio app service:

1. Check the status of the service:
   ```
   sudo systemctl status gigawatt-datacenter.service
   ```

2. Start the service:
   ```
   sudo systemctl start gigawatt-datacenter.service
   ```

3. Stop the service:
   ```
   sudo systemctl stop gigawatt-datacenter.service
   ```

4. Restart the service:
   ```
   sudo systemctl restart gigawatt-datacenter.service
   ```

5. View service logs:
   ```
   sudo journalctl -u gigawatt-datacenter.service
   ```

### Updating the Application

To update the application with the latest code:

1. SSH into the server:
   ```
   ssh user@your_server_ip
   ```

2. Navigate to the project directory:
   ```
   cd /var/www/gigawatt-datacenter
   ```

3. Pull the latest changes from Git:
   ```
   git pull origin main
   ```

4. Install any new dependencies:
   ```
   source dataEnv/bin/activate
   pip install -r requirements.txt
   ```

5. Restart the service to apply changes:
   ```
   sudo systemctl restart gigawatt-datacenter.service
   ```

### Checking Logs

To check the application logs for errors:

1. View the systemd service logs:
   ```
   sudo journalctl -u gigawatt-datacenter.service
   ```

2. Check Nginx error logs:
   ```
   sudo tail -f /var/log/nginx/error.log
   ```

3. Check Nginx access logs:
   ```
   sudo tail -f /var/log/nginx/access.log
   ```

### Useful Commands

- To check which process is using port 7860:
  ```
  sudo lsof -i :7860
  ```

- To restart Nginx:
  ```
  sudo systemctl restart nginx
  ```

### Setting Up Nginx

1. Install Nginx if not already installed:
   ```
   sudo apt update
   sudo apt install nginx
   ```

2. Create a new Nginx server block configuration:
   ```
   sudo nano /etc/nginx/sites-available/gigawatt-datacenter
   ```

3. Add the following content to the file:
   ```nginx
   server {
       listen 80;
       server_name gigawattdatacenter.com www.gigawattdatacenter.com;

       location / {
           proxy_pass http://localhost:7860;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

4. Create a symbolic link to enable the site:
   ```
   sudo ln -s /etc/nginx/sites-available/gigawatt-datacenter /etc/nginx/sites-enabled/
   ```

5. Test Nginx configuration:
   ```
   sudo nginx -t
   ```

6. If the test is successful, restart Nginx:
   ```
   sudo systemctl restart nginx
   ```

### Reviewing Nginx Settings

To review your Nginx settings for gigawattdatacenter.com:

1. View the Nginx configuration file:
   ```
   sudo cat /etc/nginx/sites-available/gigawatt-datacenter
   ```

2. Check if the symbolic link exists:
   ```
   ls -l /etc/nginx/sites-enabled/gigawatt-datacenter
   ```

3. Verify Nginx is listening on port 80:
   ```
   sudo netstat -tlnp | grep nginx
   ```

4. Check Nginx error logs for any issues:
   ```
   sudo tail -f /var/log/nginx/error.log
   ```

Remember to always check the logs after restarting the server to ensure everything is running correctly.
