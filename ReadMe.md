# Gigawatt Data Center - Energy Analysis

Inspired by a blog from [Austin Vernon](https://austinvernon.site/blog/datacenterpv.html) 

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
python solar.py
```


# Server Management

## Setting Up Systemd Service

To manage the Eire Data Gradio app as a systemd service, follow these steps:

1. Create a new user for running the app:
   ```
   sudo adduser eire-app
   ```

2. Change ownership of the project directory:
   ```
   sudo chown -R eire-app:eire-app /var/www/eire-data
   ```

3. Create a systemd service file:
   ```
   sudo nano /etc/systemd/system/eire-data.service
   ```

4. Add the following content to the file:
   ```ini
   [Unit]
   Description=Eire Data Gradio App
   After=network.target

   [Service]
   User=eire-app
   WorkingDirectory=/var/www/eire-data
   ExecStart=/var/www/eire-data/dataEnv/bin/python /var/www/eire-data/app/app.py
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
   sudo systemctl enable eire-data.service
   ```

8. Start the service:
   ```
   sudo systemctl start eire-data.service
   ```

## Managing the Application Service

Use these commands to manage the Eire Data Gradio app service:

1. Check the status of the service:
   ```
   sudo systemctl status eire-data.service
   ```

2. Start the service:
   ```
   sudo systemctl start eire-data.service
   ```

3. Stop the service:
   ```
   sudo systemctl stop eire-data.service
   ```

4. Restart the service:
   ```
   sudo systemctl restart eire-data.service
   ```

5. View service logs:
   ```
   sudo journalctl -u eire-data.service
   ```

## Updating the Application

To update the application with the latest code:

1. SSH into the server:
   ```
   ssh user@your_server_ip
   ```

2. Navigate to the project directory:
   ```
   cd /var/www/eire-data
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
   sudo systemctl restart eire-data.service
   ```

## Checking Logs

To check the application logs for errors:

1. View the systemd service logs:
   ```
   sudo journalctl -u eire-data.service
   ```

2. Check Nginx error logs:
   ```
   sudo tail -f /var/log/nginx/error.log
   ```

3. Check Nginx access logs:
   ```
   sudo tail -f /var/log/nginx/access.log
   ```

## Useful Commands

- To check which process is using port 7860:
  ```
  sudo lsof -i :7860
  ```

- To restart Nginx:
  ```
  sudo systemctl restart nginx
  ```

Remember to always check the logs after restarting the server to ensure everything is running correctly.