# Remote SSH Examples

This document provides practical examples of using Agent Warden with remote SSH locations.

## Prerequisites

1. **SSH Access Configured**
   ```bash
   # Test your SSH connection
   ssh user@server.com 'echo "Connected successfully"'
   ```

2. **SSH Config Setup** (Optional but recommended)
   ```bash
   # Edit ~/.ssh/config
   cat >> ~/.ssh/config << 'EOF'
   Host devserver
       HostName dev.example.com
       User developer
       Port 22
       IdentityFile ~/.ssh/id_rsa
   
   Host prodserver
       HostName prod.example.com
       User deploy
       Port 2222
       IdentityFile ~/.ssh/prod_key
   EOF
   ```

## Basic Remote Installation

### Install to Remote Server

```bash
# Install Augment rules to remote project
warden install user@server.com:/var/www/myapp \
    --target augment \
    --rules coding-no-emoji git-commit

# Using SSH config alias
warden install devserver:/home/dev/project \
    --target cursor \
    --rules coding-standards
```

### Install Multiple Targets to Same Remote Project

```bash
# Install Augment target
warden install server:/var/www/app \
    --target augment \
    --rules coding-no-emoji

# Add Cursor target to same project
warden install server:/var/www/app \
    --target cursor \
    --rules coding-no-emoji

# Both targets now managed for this remote project
warden project list
```

## Managing Remote Projects

### Check Status

```bash
# List all projects (shows local and remote)
warden project list

# Check specific remote project status
warden status myapp

# Check all projects for updates
warden status
```

### Update Remote Projects

```bash
# Update specific remote project
warden project update myapp

# Update all projects (including remote)
warden project update-all

# Force update with conflicts
warden project update myapp --force
```

### Add More Rules to Remote Project

```bash
# Add rules to existing remote project
warden install --project myapp --rules new-rule

# Add to specific target
warden install --project myapp --target augment --rules typescript-rules
```

## Advanced Scenarios

### Multiple Remote Servers

```bash
# Development server
warden install dev@dev.example.com:/var/www/app \
    --target augment \
    --rules coding-standards \
    --name dev-app

# Staging server
warden install deploy@staging.example.com:/var/www/app \
    --target augment \
    --rules coding-standards \
    --name staging-app

# Production server
warden install deploy@prod.example.com:/var/www/app \
    --target augment \
    --rules coding-standards \
    --name prod-app

# Update all environments at once
warden project update-all
```

### Using ProxyJump

```bash
# SSH config with bastion host
cat >> ~/.ssh/config << 'EOF'
Host internal-server
    HostName 10.0.1.100
    User developer
    ProxyJump bastion.example.com
EOF

# Install through bastion
warden install internal-server:/opt/app \
    --target augment \
    --rules security-rules
```

### Mixed Local and Remote Projects

```bash
# Local project
warden install ~/local-project \
    --target augment \
    --rules coding-standards

# Remote project
warden install server:/remote-project \
    --target augment \
    --rules coding-standards

# Both managed together
warden project list
warden status
warden project update-all
```

## Troubleshooting

### Connection Issues

```bash
# Test SSH connection
ssh user@server.com 'echo "OK"'

# Check if remote path exists
ssh user@server.com 'ls -la /var/www/project'

# Verify write permissions
ssh user@server.com 'touch /var/www/project/test && rm /var/www/project/test'
```

### Transfer Tool Issues

```bash
# Check if rsync is available
which rsync

# If rsync not available, Agent Warden will fall back to scp
# Install rsync for better performance:
# Ubuntu/Debian: sudo apt-get install rsync
# macOS: brew install rsync
```

### Permission Errors

```bash
# Ensure you have write access to remote directory
ssh user@server.com 'ls -ld /var/www/project'

# Fix permissions if needed
ssh user@server.com 'sudo chown -R user:user /var/www/project'
```

## Controlling Remote Updates

If you have remote projects that require password authentication or are temporarily unavailable, you can disable them in global update commands:

```bash
# Disable remote project updates in global commands
warden config --update-remote false

# Now these commands will skip remote projects:
warden status
warden project update-all

# Individual remote projects can still be updated:
warden project update my-remote-project

# Re-enable remote updates
warden config --update-remote true

# Check current setting
warden config --show
```

**When to disable remote updates:**
- Remote servers require password authentication (would interrupt automated updates)
- Temporary network issues or VPN disconnections
- Remote servers are offline or under maintenance
- You want to update only local projects quickly

## Best Practices

1. **Use SSH Config Aliases**
   - Easier to remember and type
   - Centralized SSH configuration
   - Supports complex setups (ProxyJump, custom ports, etc.)

2. **Name Your Projects**
   - Use `--name` for descriptive project names
   - Especially useful when managing multiple remote servers

3. **Test SSH First**
   - Always verify SSH connection before using Agent Warden
   - Ensure write permissions on remote directories

4. **Configure Remote Updates**
   - Disable remote updates if you have password-protected servers
   - Use `warden config --update-remote false` to skip remote in global commands
   - Individual remote projects can still be updated directly

5. **Regular Updates**
   - Use `warden status` to check for outdated rules
   - Update all projects regularly with `warden project update-all`

6. **Backup State**
   - Agent Warden state is stored locally in `.warden_state.json`
   - Back up this file to preserve remote project tracking

