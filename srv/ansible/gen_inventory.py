#!/usr/bin/env python3
import sys, json
from jinja2 import Environment, FileSystemLoader

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 gen_inventory.py terraform_output.json", file=sys.stderr)
        sys.exit(1)

    tf = json.load(open(sys.argv[1]))
    ips = tf.get("services_public_ips", {}).get("value", {})

    env = Environment(
        loader=FileSystemLoader('.'),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tpl = env.get_template('hosts.ini.j2')
    inventory = tpl.render(private_ips=ips)

    with open('hosts.ini', 'w') as f:
        f.write(inventory)

    print("✅ INI inventory written to hosts.ini", file=sys.stderr)

if __name__ == "__main__":
    main()
