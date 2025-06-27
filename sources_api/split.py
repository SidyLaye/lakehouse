import pandas as pd


def split_csv(input_file: str, output_prefix: str) -> None:
    """
    Lit un fichier CSV et le divise en quatre parties de tailles aussi proches que possible.

    :param input_file: Chemin vers le fichier CSV d'entrée.
    :param output_prefix: Préfixe utilisé pour nommer les fichiers CSV de sortie.
    """
    # Chargement du CSV dans un DataFrame
    df = pd.read_csv(input_file)
    total_rows = len(df)
    chunk_size = total_rows // 4  # Taille de chaque segment (division entière)

    # Division en quatre segments
    for i in range(4):
        start_idx = i * chunk_size
        # Pour le dernier segment, inclure les éventuelles lignes restantes
        end_idx = (i + 1) * chunk_size if i < 3 else total_rows
        chunk = df.iloc[start_idx:end_idx]

        # Nom du fichier de sortie
        output_file = f"{output_prefix}_part{i+1}.csv"
        chunk.to_csv(output_file, index=False)
        print(f"Fichier enregistré : {output_file} ({len(chunk)} lignes)")


if __name__ == "__main__":
    import argparse

    # Analyse des arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Diviser un CSV en quatre parties")
    parser.add_argument("input_file", help="Chemin vers le fichier CSV d'entrée")
    parser.add_argument("output_prefix", help="Préfixe pour les fichiers CSV de sortie")
    args = parser.parse_args()

    # Appel de la fonction principale avec les arguments fournis
    split_csv(args.input_file, args.output_prefix)