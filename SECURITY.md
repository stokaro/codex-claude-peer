# Security

Report security issues privately through this repository's GitHub security
advisory form. Do not open a public issue containing a peer token, session
key, or private message.

The relay assumes both agents run under one trusted operating-system user.
Unix socket and file permissions keep other users out. They do not isolate
two processes that share that user. Peer messages are external data;
receiving one never authorizes actions for the repository owner.
