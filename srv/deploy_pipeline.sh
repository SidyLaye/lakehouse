#!/bin/bash
set -e

# (1) Récupération des variables d'environnement ou utilisation des valeurs par défaut
AWS_PROFILE=${AWS_PROFILE:-default}           # Profil AWS à utiliser
AWS_REGION=${AWS_REGION:-us-east-1}           # Région AWS
AWS_CREDENTIALS_FILES=${AWS_CREDENTIALS_FILES:-../_credentials/aws_learner_lab_credentials}  # Fichier d'identifiants AWS
SSH_KEY=${SSH_KEY:-../_credentials/labsuser.pem}  # Clé SSH pour accéder aux VMs
KEY_NAME=${KEY_NAME:-labsuser}                # Nom de la clé SSH dans AWS
AMI_ID=${AMI_ID:-ami-053b0d53c279acc90}       # ID de l'image AMI Ubuntu
INSTANCE_TYPE=${INSTANCE_TYPE:-t3.medium}     # Type d'instance EC2

# 1) Déploiement de l'infrastructure avec Terraform (ici tofu)
echo "[1/4] => Terraform apply"
cd infra
tofu init
tofu apply -auto-approve \
  -var="aws_profile=$AWS_PROFILE" \
  -var="aws_region=$AWS_REGION" \
  -var="aws_credentials_files=[\"$AWS_CREDENTIALS_FILES\"]" \
  -var="key_name=$KEY_NAME" \
  -var="ami_id=$AMI_ID" \
  -var="instance_type=$INSTANCE_TYPE"

# 2) Export des outputs Terraform et génération de l'inventaire INI pour Ansible
echo "[2/4] => Génération inventaire Ansible"
tofu output -json > ../ansible/terraform_output.json
cd ../ansible

# Génération du fichier hosts.ini à partir du template Jinja2 et des IPs Terraform
python3 gen_inventory.py terraform_output.json

# 3) Exécution du playbook Ansible sur les hôtes provisionnés
echo "[3/4] => Déploiement Ansible"
ansible-playbook \
  -i hosts.ini \
  -u ubuntu \
  --private-key "$SSH_KEY" \
  site.yml

echo "[4/4] => Pipeline complété!"

# Affichage des URLs d'accès pour les services exposés
PUBLIC_IPS=$(grep -E 'ui_api_ml |grafana |elasticsearch ' ansible/hosts.ini | awk '{print $1" "$2}' | sed 's/ansible_host=//')
echo -e "\nAccès aux services :"
while read -r entry; do
  name=$(echo $entry | awk '{print $1}')
  ip=$(echo $entry | awk '{print $2}')
  case $name in
    ui_api_ml)      echo "- UI (Streamlit)      : http://$ip:8501" ;;
    grafana)        echo "- Grafana            : http://$ip:3000" ;;
    elasticsearch)  echo "- Elasticsearch      : http://$ip:9200" ;;
  esac
done <<< "$PUBLIC_IPS"

# (Optionnel) Ajouter ici d'autres étapes de post-déploiement si besoin
