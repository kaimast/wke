FROM ubuntu:24.04

RUN apt-get update && \
    apt-get install -y openssh-server && \
    mkdir /var/run/sshd

# Create a non-root user 'testuser' with password 'testpassword'
RUN useradd -m -s /bin/bash testuser && \
    mkdir -p /home/testuser/.ssh && \
    chmod 700 /home/testuser/.ssh

# Add the public key for testuser
RUN echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE0R4te4bZOK7gn8RCrW1REIAlyGKHFGFQpkaxK+Olkh testuser@wke" > /home/testuser/.ssh/authorized_keys && \
     chmod 600 /home/testuser/.ssh/authorized_keys && \
     chown -R testuser:testuser /home/testuser/.ssh

# Configure SSH to allow root login and password authentication
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Expose port 22 for SSH
EXPOSE 22

# Start the SSH service
CMD ["/usr/sbin/sshd", "-D"]
