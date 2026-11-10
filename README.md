# US Accidents — ETL, Data Warehouse e Análise de Dados

Projeto desenvolvido como parte da disciplina de Banco de Dados III, no curso de Sistemas de Informação.

**Autor:** Samuel Silva Santos

## Sobre o projeto

Este projeto utiliza a base US Accidents (2016–2023) para estudar a distribuição dos acidentes de trânsito nos Estados Unidos, considerando localização, período do ano, condições climáticas e severidade.

O objetivo é transformar uma base de dados extensa em uma estrutura organizada, que permita realizar consultas, identificar padrões e construir visualizações.

Além de ser um trabalho acadêmico, o projeto também faz parte do meu portfólio de estudos em Engenharia e Ciência de Dados.

## Tecnologias utilizadas

- **Python:** desenvolvimento dos scripts de diagnóstico, tratamento e validação.
- **SQL:** consultas, transformações e criação das tabelas.
- **DuckDB:** armazenamento e processamento analítico dos dados.
- **Power BI:** ferramenta escolhida para a etapa de visualização.

## Base de dados

O projeto utiliza a base pública US Accidents, com aproximadamente 7,7 milhões de registros e 46 colunas.

O período analisado vai de janeiro de 2016 a março de 2023.

O arquivo original não está incluído no repositório devido ao seu tamanho. Para conhecer a base, consulte:

[US Accidents — Kaggle](https://www.kaggle.com/datasets/sobhanmoosavi/us-accidents)

## Arquitetura

O processamento foi organizado nas seguintes etapas:

**CSV original → Staging → Data Warehouse → Análises → Power BI**

A staging recebe os dados tratados e padronizados. O Data Warehouse organiza essas informações em um modelo dimensional, facilitando consultas e análises.

## Modelo dimensional

Foi implementado um modelo estrela com a tabela central `FatoAcidente` e oito dimensões:

| Tabela | Finalidade |
|---|---|
| DimData | Datas, meses, anos e estações |
| DimHora | Horários dos acidentes |
| DimLocalizacao | Estados, cidades e outras informações geográficas |
| DimCondicaoClimatica | Condições meteorológicas |
| DimLuminosidade | Condições de iluminação |
| DimSeveridade | Níveis de impacto dos acidentes |
| DimVia | Características das vias |
| DimFonte | Origem dos registros |

A tabela fato contém 7.728.394 acidentes, com um registro por acidente.

## Desenvolvimento realizado

### 1. Diagnóstico e qualidade

Foram realizadas verificações de estrutura, valores ausentes, duplicidades e possíveis inconsistências.

### 2. Tratamento dos dados

Foram implementadas conversões de unidades, padronização de datas e identificação de valores suspeitos.

### 3. Construção do Data Warehouse

Foram criadas a tabela staging, as oito dimensões e a tabela fato, utilizando Python e DuckDB.

### 4. Validação

Foram executados testes para verificar a integridade das chaves, a preservação dos registros e a correspondência das medidas.

O Data Warehouse preservou os 7.728.394 acidentes da base original.

### 5. Análises exploratórias

Foram realizadas análises por:

- Ano e fonte dos registros.
- Estado.
- Estação do ano.
- Condição climática.
- Severidade.
- Cobertura temporal das fontes.

Também foi produzido um conjunto integrado com 100.386 combinações analíticas e uma série mensal de 87 meses.

## Principais resultados

A Califórnia apresentou o maior número de acidentes registrados, seguida pela Flórida e pelo Texas.

O outono concentrou o maior volume de registros quando agrupamos os acidentes por estação.

A condição climática `Fair` foi a mais frequente entre os acidentes registrados.

Esses resultados descrevem a base estudada. Não representam necessariamente maior risco de acidentes, pois a quantidade de registros pode ser influenciada pelo volume de tráfego, pela cobertura das fontes e por diferenças regionais.

## Limitações identificadas

Durante a análise, foram identificadas mudanças importantes na participação das fontes ao longo dos anos.

Também foram encontrados períodos sem registros em determinadas fontes.

Por esse motivo, comparações temporais e projeções precisam considerar essas limitações.

A severidade utilizada no projeto representa o impacto do acidente sobre o trânsito, não sendo equivalente a uma classificação de vítimas ou fatalidades.

## Estrutura do repositório

- `scripts/`: scripts Python utilizados no desenvolvimento.
- `resultados/`: arquivos CSV e JSON com resultados das análises.
- `dados/`: arquivos de dados locais, não versionados.
- `.gitignore`: regras para evitar a publicação de arquivos grandes e temporários.

## Próximas etapas

- Desenvolver os dashboards no Power BI.
- Criar visualizações interativas.
- Documentar os indicadores e medidas.
- Avaliar a viabilidade de uma projeção para 2026.
- Finalizar a apresentação acadêmica.

## Autor

**Samuel Silva Santos**

Estudante de Sistemas de Informação, com interesse em Engenharia de Software, Engenharia de Dados e Ciência de Dados.

[Meu GitHub](https://github.com/Samuel-SSantos)