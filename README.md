# Code Generation using a JSON code book and a Schema file

This repository contains code to generate code from the JSON codebook file which conforms to a schema

Please read the CodeGenerationFromJson.pdf in the 'doc' folder for a detailed view of this project.

## Usage

```
$> cd src

$>python main.py -s <schema file> -c <codebook file> -o <output file>

$>python main.py -s codebook_schema.json -c sample_codebook.json -o generated.py

```
