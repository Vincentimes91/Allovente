# Allovente SSH Gateway — Mistral Workflows

Passerelle SSH permanente vers le VPS Allovente (57.129.153.119), déployée
en *managed deployment* Mistral. Les workflows exécutent des commandes sur le
VPS avec une clé SSH dédiée, sans jamais exposer d'identifiants dans le code.

## Workflows

| Nom | Entrée | Rôle |
| --- | --- | --- |
| `allovente-ssh` | `{"command": "...", "timeout_seconds": 120}` | Exécute une commande shell sur le VPS |
| `allovente-read-file` | `{"path": "/var/log/...", "max_bytes": 500000}` | Lit un fichier via SFTP |

Sortie commune : `{"exit_code", "stdout", "stderr", "timed_out", "error"}`.

## Sécurité

- Clé privée lue depuis la variable d'environnement `ALOVENTE_SSH_KEY`
  (secret de workspace Mistral lié au déploiement).
- Clé hôte SSH du VPS **épinglée** dans `ssh_exec.py` (politique `RejectPolicy`,
  aucune acceptation aveugle de clé inconnue).
- Clé sans agent, sans mot de passe, sans `look_for_keys`.

## Déploiement

Déploiement géré Mistral, nom : `allovente-ssh-gateway`.
Secret workspace requis : `allovente_ssh_key` (contenu de la clé privée Ed25519),
lié à la variable d'environnement `ALOVENTE_SSH_KEY`.
