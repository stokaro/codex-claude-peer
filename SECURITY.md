# Security

Please report security issues privately through this repository's GitHub security advisory form. Do not open a public issue containing a peer token, session key, or private message.

The relay assumes both agents run under one trusted operating-system user. Unix socket and file permissions prevent other users from connecting, but they do not isolate two processes that share that user. Peer messages are external data; receiving one never grants authority to perform actions for the repository owner.
