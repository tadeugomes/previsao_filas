# Investigacao das Features de Mare/Clima

## Resumo Executivo

Apos analise detalhada do codigo e dos datasets de mare/clima, foram identificados **5 problemas criticos** que explicam por que as features de mare/clima nao estavam contribuindo para melhoria do modelo preditivo.

## Problemas Identificados

### 1. Dataset v4_real NAO estava sendo usado

**Problema:** O codigo referenciava `dados_historicos_portos_hibridos_arco_norte_v2.parquet` que contem apenas dados de 2020 (26k registros), ignorando o `dados_historicos_portos_hibridos_arco_norte_v4_real.parquet` com dados de 2020-2024 (105k registros).

**Impacto:** Para portos do Arco Norte (Vila do Conde, Barcarena, Santarem), o modelo so tinha dados climaticos de 1 ano ao inves de 5 anos.

**Correcao aplicada:** Atualizado `MARE_CLIMA_DATASET_3` para usar v4_real.

### 2. Bug de normalizacao de nomes de portos

**Problema:** A funcao `_normalizar_porto_clima()` removia incorretamente sufixos que pareciam siglas de UF, mesmo quando faziam parte do nome do porto.

**Exemplo:**
- "Porto de Suape" -> "SUA" (incorreto, removia "PE")
- Esperado: "SUAPE"

**Impacto:** O porto de Suape nao recebia dados climaticos do dataset.

**Correcao aplicada:** Logica melhorada para so remover UF quando ha indicadores claros (parenteses ou nomes longos).

### 3. Features oceanograficas nao estavam sendo usadas

**Problema:** O dataset `dados_historicos_complementares_portos_oceanicos_v2.parquet` contem dados valiosos de:
- `wave_height`: altura de ondas (importante para ressacas)
- `frente_fria`: indicador de frentes frias
- `pressao_anomalia`: anomalia de pressao atmosferica

Esses dados NAO estavam sendo integrados ao modelo.

**Correcao aplicada:** Adicionada integracao de features oceanograficas:
- `wave_height_max`: altura maxima de onda no dia
- `wave_height_media`: altura media de onda
- `frente_fria`: indicador binario
- `pressao_anomalia`: anomalia de pressao
- `ressaca`: feature derivada (ondas > 2.5m)

### 4. Dados faltantes no v4_real

**Observacao:** O dataset v4_real tem alta taxa de valores faltantes:
- `vazao_rio_m3s`: 100% NaN (dados de vazao nao disponiveis)
- `precip`: 30.3% NaN
- `mare_astronomica_m`: 33.3% NaN
- `wind_speed_10m`: 26% NaN

**Recomendacao:** Considerar usar interpolacao ou dados alternativos para preencher lacunas.

### 5. Cobertura de portos nos datasets

| Dataset | Portos | Periodo | Features principais |
|---------|--------|---------|---------------------|
| portos_hibridos | Rio Grande, Paranagua, Antonina | 2020-2024 | mare, vento, pressao, vazao |
| oceanicos_v2 | 13 portos | 2020-2025 | ondas, frente_fria, pressao_anomalia |
| arco_norte_v4_real | Vila do Conde, Barcarena, Santarem | 2020-2024 | mare, vento, pressao |

## Melhorias Implementadas

1. **Referencia correta ao dataset v4_real**
   - Arquivo: `plano_1.py` linha 34

2. **Correcao da normalizacao de portos**
   - Funcao: `_normalizar_porto_clima()`
   - Logica melhorada para detectar quando UF e parte do nome vs sufixo

3. **Integracao de features oceanograficas**
   - Funcao: `carregar_clima_mare_clima_diario()`
   - Novas features: wave_height_max, wave_height_media, frente_fria, pressao_anomalia, ressaca

4. **Validacao de features disponiveis**
   - Funcao: `preparar_dados()`
   - Filtra features que nao existem no dataframe para evitar erros

## Recomendacoes Futuras

### Curto prazo

1. **Retreinar modelos** com as correcoes aplicadas para avaliar melhoria de performance

2. **Monitorar cobertura de dados** - Verificar quantos registros estao recebendo dados de mare/clima

3. **Feature importance** - Apos retreinamento, verificar importancia das novas features oceanograficas

### Medio prazo

1. **Preencher dados faltantes de vazao** - Os dados de vazao fluvial (100% NaN no v4_real) podem ser obtidos da ANA (Agencia Nacional de Aguas)

2. **Adicionar mais portos ao mapeamento** - O dicionario `MARE_PORT_FILE_BY_NORM` nao inclui todos os portos

3. **Features de interacao** - Criar features combinando mare + vento (ex: restricao operacional)

### Longo prazo

1. **Dados de mare em tempo real** - Integrar previsoes de mare da DHN (Diretoria de Hidrografia e Navegacao)

2. **Modelo especifico por regiao** - Portos do Arco Norte tem dinamica diferente (influencia fluvial)

3. **Validacao com dados operacionais** - Comparar previsoes com restricoes operacionais reais

## Estrutura dos Arquivos Modificados

```
plano_1.py
├── MARE_CLIMA_DATASET_3 -> v4_real (linha 34)
├── _normalizar_porto_clima() -> Corrigida (linhas 367-388)
├── carregar_clima_mare_clima_diario() -> + features oceanograficas (linhas 570-635)
├── integrar_clima_mare_clima() -> + wave, frente_fria, ressaca (linhas 664-678)
└── preparar_dados() -> + features e validacao (linhas 1047-1071)
```

## Conclusao

A ablacao que mostrou baseline INMET como melhor opcao era enganosa - as features de mare/clima nao estavam sendo integradas corretamente devido aos bugs identificados. Com as correcoes aplicadas, esperamos que as features oceanograficas (especialmente ondas e frentes frias) contribuam significativamente para a previsao de tempo de espera em portos costeiros.

---
*Documento gerado em: 2026-01-22*
*Commit: 38c854e*
