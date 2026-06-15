# Base image — UBI9 Node.js 20, works on ROSA HCP with restricted-v2 SCC
FROM registry.access.redhat.com/ubi9/nodejs-20:latest

# Run as non-root — required for restricted-v2 SCC on ROSA HCP
USER 1001

WORKDIR /opt/app-root/src

# Copy package files and install dependencies
COPY --chown=1001:0 package*.json ./
RUN npm install --production

# Copy application source
COPY --chown=1001:0 server.js .

# Expose port 8080 — standard for OpenShift (non-privileged port)
EXPOSE 8080

CMD ["node", "server.js"]
