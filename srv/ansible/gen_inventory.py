#!/usr/bin/env python3
import sys, json
from jinja2 import Environment, FileSystemLoader


def main():
    # Vérifie que le script reçoit bien le fichier terraform_output.json en argument
    if len(sys.argv) != 2:
        print("Utilisation : python3 gen_inventory.py terraform_output.json", file=sys.stderr)
        sys.exit(1)

    # Charge les sorties Terraform (IPs des services)
    tf = json.load(open(sys.argv[1]))
    ips = tf.get("services_public_ips", {}).get("value", {})

    # Prépare l'environnement Jinja2 pour générer le fichier d'inventaire Ansible
    env = Environment(
        loader=FileSystemLoader('.'),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tpl = env.get_template('hosts.ini.j2')
    inventory = tpl.render(private_ips=ips)

    # Écrit l'inventaire généré dans hosts.ini
    with open('hosts.ini', 'w') as f:
        f.write(inventory)

    print("✅ Inventaire INI écrit dans hosts.ini", file=sys.stderr)

if __name__ == "__main__":
    main()
