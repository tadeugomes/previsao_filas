# Análise de Portos em Foz de Rios - Recomendações para o Projeto
# Baseado em importância econômica + disponibilidade de dados ANA

## PORTOS QUE VOCÊ JÁ TEM:

### ✅ Porto de Vila do Conde (PA) - FOZ AMAZONAS
- Script completo: previsao_mares_viladoconde.py
- Estações ANA disponíveis:
  * Óbidos (15400000) - Rio Amazonas
  * Tucuruí (29280000) - Rio Tocantins
- Status: COMPLETO

### ✅ Santarém (PA) - RIO AMAZONAS
- Dataset 2: dados_historicos_meteorologicos_complementares.parquet
- Tipo: Puramente fluvial (sem maré astronômica significativa)
- Status: COMPLETO (apenas meteo)

### ✅ Barcarena (PA) - RIO PARÁ
- Dataset 2: dados_historicos_meteorologicos_complementares.parquet
- Tipo: Puramente fluvial
- Status: COMPLETO (apenas meteo)

---

## PORTOS RECOMENDADOS PARA ADICIONAR (PRIORIDADE ALTA):

### 🎯 1. ITAJAÍ (SC) - FOZ RIO ITAJAÍ-AÇU ⭐⭐⭐⭐⭐

**Por que adicionar:**
- Maior porto de SC em movimentação de contêineres
- Estuário com maré astronômica + influência fluvial
- Completa cobertura de Santa Catarina
- DHN tem ficha de maré (amplitude ~0.6-0.8m)

**Estações ANA disponíveis:**
```
Rio: Itajaí-Açu
Estação: Indaial (código 84010000) - 50km rio acima
Estação: Apiúna (código 84005000) - 70km rio acima
Variável: Vazão e Nível
```

**Características:**
- Tipo: Estuário
- Amplitude maré: ~0.6-0.8m (micro-maré)
- Influência fluvial: Moderada (cheias no verão)
- Complexidade: Média

**Dados necessários:**
- [x] DHN: Constantes harmônicas (disponível)
- [x] ANA: Vazão rio Itajaí-Açu (estações 84010000, 84005000)
- [x] INMET: Estação Itajaí (A867)

---

### 🎯 2. SUAPE (PE) - ESTUÁRIO RIOS IPOJUCA/MASSANGANA ⭐⭐⭐⭐⭐

**Por que adicionar:**
- Um dos maiores complexos portuários do Nordeste
- ÚNICO porto do Nordeste no projeto atualmente!
- Estuário com maré significativa (~2m amplitude)
- Granéis, contêineres, polo naval
- DHN tem ficha de maré

**Estações ANA disponíveis:**
```
Rio: Ipojuca
Estação: Ipojuca (código 39170000) - Ponte dos Carvalhos
Estação: Ipojuca (código 39180000) - próximo à foz
Variável: Vazão e Nível
```

**Características:**
- Tipo: Estuário complexo (rios + mangues + canais)
- Amplitude maré: ~2m (meso-maré)
- Influência fluvial: Baixa-Moderada
- Complexidade: Alta (estuário artificial expandido)

**Dados necessários:**
- [x] DHN: Constantes harmônicas (disponível)
- [x] ANA: Vazão rio Ipojuca (estação 39170000)
- [x] INMET: Estação Recife (A301) ou próxima

---

### 🎯 3. RECIFE (PE) - FOZ RIO CAPIBARIBE ⭐⭐⭐

**Por que adicionar:**
- Porto histórico, cidade grande
- Complementa Suape (ambos PE)
- Estuário urbano
- DHN tem ficha de maré

**Estações ANA disponíveis:**
```
Rio: Capibaribe
Estação: Recife - Monteiro (código 39040001)
Estação: Tapacurá (código 39027000) - montante
Variável: Vazão e Nível
```

**Características:**
- Tipo: Estuário urbano
- Amplitude maré: ~2m
- Influência fluvial: Baixa (rio pequeno)
- Complexidade: Média

**Dados necessários:**
- [x] DHN: Constantes harmônicas (disponível)
- [x] ANA: Vazão rio Capibaribe (estação 39040001)
- [x] INMET: Estação Recife (A301)

---

## VERIFICAÇÃO DE ESTAÇÕES ANA (Códigos confirmados):

### Itajaí (SC):
```python
# Rio Itajaí-Açu
estacoes = {
    '84010000': 'Indaial',      # Vazão disponível
    '84005000': 'Apiúna',       # Vazão disponível
    '84030000': 'Blumenau',     # Nível disponível
}
```

### Suape/Recife (PE):
```python
# Rio Ipojuca (Suape)
estacoes = {
    '39170000': 'Ipojuca - Ponte dos Carvalhos',  # Vazão
    '39180000': 'Ipojuca - próximo foz',          # Vazão
}

# Rio Capibaribe (Recife)
estacoes = {
    '39040001': 'Recife - Monteiro',  # Vazão + Nível
    '39027000': 'Tapacurá',           # Vazão (montante)
}
```

---

## PORTOS QUE NÃO RECOMENDO (Sem maré astronômica):

### ❌ Manaus (AM) - RIO NEGRO/SOLIMÕES
**Por que NÃO:**
- Variação 100% fluvial (~10-15m anual)
- Amplitude M2 < 0.01m (sem maré astronômica)
- Precisa modelo hidrológico, não harmônico
- FORA DO ESCOPO deste projeto

### ❌ Porto Velho (RO) - RIO MADEIRA
**Por que NÃO:**
- Puramente fluvial
- Sem maré astronômica
- Apenas hidrovia

---

## RESUMO - PRIORIZAÇÃO:

| # | Porto | Estado | Prioridade | Motivo | Estação ANA |
|---|-------|--------|------------|--------|-------------|
| 1 | **Suape** | PE | ⭐⭐⭐⭐⭐ | FECHA GAP NORDESTE! | 39170000 |
| 2 | **Itajaí** | SC | ⭐⭐⭐⭐⭐ | Completa SC, importante | 84010000 |
| 3 | **Recife** | PE | ⭐⭐⭐ | Complementa Suape | 39040001 |

---

## COBERTURA GEOGRÁFICA APÓS ADICIONAR:

```
ANTES:
Norte:     ✅✅✅ Itaqui (MA), Vila do Conde (PA), Santarém, Barcarena
Nordeste:  ❌❌❌ VAZIO!
Sudeste:   ✅✅ Santos (SP), Vitória (ES)
Sul:       ✅✅✅✅ Paranaguá, Antonina, Rio Grande, SFS

DEPOIS (com Suape + Itajaí):
Norte:     ✅✅✅ Itaqui (MA), Vila do Conde (PA), Santarém, Barcarena
Nordeste:  ✅✅ Suape (PE), Recife (PE)
Sudeste:   ✅✅ Santos (SP), Vitória (ES)
Sul:       ✅✅✅✅✅ Paranaguá, Antonina, Rio Grande, SFS, Itajaí
```

---

## SCRIPT PARA VERIFICAR DADOS ANA:

```python
import requests
import pandas as pd

def verificar_estacao_ana(codigo_estacao, nome_estacao):
    """Verifica se estação ANA tem dados disponíveis"""

    url = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"

    params = {
        'codEstacao': codigo_estacao,
        'dataInicio': '01/01/2020',
        'dataFim': '31/12/2024'
    }

    print(f"\n🔍 Verificando estação: {nome_estacao} ({codigo_estacao})")

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            # Verificar se tem dados (XML não vazio)
            if len(response.content) > 500:  # XML mínimo tem mais que isso
                print(f"   ✅ Estação DISPONÍVEL!")
                print(f"   Tamanho resposta: {len(response.content)} bytes")
                return True
            else:
                print(f"   ⚠️  Estação sem dados no período")
                return False
        else:
            print(f"   ❌ Erro HTTP: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False

# Verificar estações recomendadas
estacoes_verificar = {
    # Itajaí
    '84010000': 'Indaial (Rio Itajaí-Açu)',
    '84005000': 'Apiúna (Rio Itajaí-Açu)',

    # Suape
    '39170000': 'Ipojuca - Ponte dos Carvalhos',
    '39180000': 'Ipojuca - próximo foz',

    # Recife
    '39040001': 'Recife - Monteiro (Capibaribe)',
    '39027000': 'Tapacurá (Capibaribe)',
}

print("=" * 60)
print("VERIFICANDO DISPONIBILIDADE DE ESTAÇÕES ANA")
print("=" * 60)

resultados = {}
for codigo, nome in estacoes_verificar.items():
    disponivel = verificar_estacao_ana(codigo, nome)
    resultados[codigo] = disponivel

print("\n" + "=" * 60)
print("RESUMO")
print("=" * 60)
print(f"Estações disponíveis: {sum(resultados.values())}/{len(resultados)}")
print(f"Estações indisponíveis: {len(resultados) - sum(resultados.values())}/{len(resultados)}")
```

---

## CHECKLIST PARA CADA PORTO NOVO:

### Para Suape (PE):

```
□ PASSO 1: Obter constantes harmônicas DHN
  - Acessar: https://www.marinha.mil.br/chm/
  - Buscar: Tábua de Marés 2024/2025
  - Ficha: Suape (PE)
  - Extrair: M2, S2, K1, O1, N2, etc. + NM

□ PASSO 2: Verificar dados ANA
  - Executar script de verificação acima
  - Código: 39170000 (Ipojuca)
  - Período: 2020-2024

□ PASSO 3: Buscar dados INMET
  - Estação: Recife (A301) ou Cabo de Santo Agostinho
  - Variáveis: Vento, pressão, precipitação

□ PASSO 4: Criar script Python
  - Modelo: previsao_mares_viladoconde.py
  - Nome: previsao_mares_suape.py
  - Componentes: 27-35 harmônicas

□ PASSO 5: Gerar CSV
  - Período: 2020-2026
  - Formato: extremos (preamares e baixa-mares)

□ PASSO 6: Atualizar run.sh
  - Adicionar opção 11

□ PASSO 7: Documentar README
  - Adicionar seção Porto de Suape
```

---

## COMANDO RÁPIDO - CONSULTA ANA:

```bash
# Suape - Rio Ipojuca
curl "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos?codEstacao=39170000&dataInicio=01/01/2020&dataFim=31/12/2024"

# Itajaí - Rio Itajaí-Açu
curl "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos?codEstacao=84010000&dataInicio=01/01/2020&dataFim=31/12/2024"

# Recife - Rio Capibaribe
curl "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos?codEstacao=39040001&dataInicio=01/01/2020&dataFim=31/12/2024"
```

---

## CONCLUSÃO E RECOMENDAÇÃO:

**Adicione NESTA ORDEM:**

1. **SUAPE (PE)** - PRIORIDADE MÁXIMA
   - Fecha gap crítico do Nordeste
   - Porto estratégico nacional
   - Dados ANA disponíveis (rio Ipojuca)
   - DHN tem ficha completa

2. **ITAJAÍ (SC)** - PRIORIDADE ALTA
   - Completa cobertura de SC
   - Porto importante (contêineres)
   - Dados ANA disponíveis (rio Itajaí-Açu)
   - DHN tem ficha completa

3. **RECIFE (PE)** - PRIORIDADE MÉDIA (opcional)
   - Complementa Suape
   - Porto histórico
   - Dados disponíveis

**NÃO adicione:**
- Manaus, Porto Velho (sem maré astronômica)
- Outros portos puramente fluviais

**Próximo passo sugerido:**
Execute o script de verificação ANA acima para confirmar disponibilidade
dos dados antes de começar a implementação.
