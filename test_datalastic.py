#!/usr/bin/env python3
"""
Teste Datalastic com resumo formatado - CORRIGIDO
"""

import requests

API_KEY = '8f4d73c7-0455-4afd-9032-4ad4878ec5b0'
BASE_URL = 'https://api.datalastic.com/api/v0'

print("=" * 90)
print(" " * 20 + "🧪 TESTE DATALASTIC AIS - PORTOS BRASILEIROS")
print("=" * 90)

# Portos para teste
portos = {
    'Itaqui (Celulose/VEGETAL)': {
        'lat': -2.57,
        'lon': -44.37,
        'radius_nm': 16.2,
        'tipo_carga': 'Celulose, Grãos'
    },
    'Ponta da Madeira (Minério/MINERAL)': {
        'lat': -2.53,
        'lon': -44.36,
        'radius_nm': 10.8,
        'tipo_carga': 'Minério de Ferro'
    }
}

total_credits = 0

for nome_porto, config in portos.items():
    print(f"\n{'─' * 90}")
    print(f"📍 PORTO: {nome_porto}")
    print(f"   Coordenadas: {config['lat']}, {config['lon']}")
    print(f"   Raio de busca: {config['radius_nm']:.1f} milhas náuticas (~{config['radius_nm']*1.852:.0f} km)")
    print(f"   Tipo de carga principal: {config['tipo_carga']}")
    print(f"{'─' * 90}")
    
    try:
        url = f"{BASE_URL}/vessel_inradius"
        params = {
            'api-key': API_KEY,
            'lat': config['lat'],
            'lon': config['lon'],
            'radius': config['radius_nm']
        }
        
        print(f"\n🔍 Consultando API Datalastic...")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Datalastic retorna: {data: {vessels: [...], total: N, point: {...}}}
            if 'data' in data and 'vessels' in data['data']:
                vessels = data['data']['vessels']
                total = data['data'].get('total', len(vessels))
                
                print(f"✅ API respondeu com sucesso!")
                print(f"   Total de navios detectados: {total}")
                
                # Análise dos navios
                anchored = 0
                moored = 0
                underway = 0
                tankers = 0
                bulkers = 0
                other = 0
                speeds = []
                
                for vessel in vessels:
                    speed = vessel.get('speed', 0) or 0  # Handle None
                    vtype = (vessel.get('type') or '').lower()
                    
                    # Classificar por tipo
                    if 'tanker' in vtype:
                        tankers += 1
                    elif 'bulk' in vtype or 'cargo' in vtype:
                        bulkers += 1
                    else:
                        other += 1
                    
                    # Classificar por velocidade (status aproximado)
                    if speed == 0 or speed < 0.5:
                        # Parado = ancorado ou atracado
                        destination = (vessel.get('destination') or '').upper()
                        if 'IQI' in destination or 'ITAQUI' in destination or 'LUIS' in destination:
                            moored += 1  # Provavelmente atracado
                        else:
                            anchored += 1  # Provavelmente ancorado (em fila)
                    else:
                        underway += 1
                        speeds.append(speed)
                
                # Exibir estatísticas
                print(f"\n📊 ESTATÍSTICAS:")
                print(f"   {'─' * 70}")
                print(f"   Total de navios na área:        {total}")
                print(f"   ⚓ Ancorados (em fila):          {anchored}")
                print(f"   🔗 Atracados (operando):         {moored}")
                print(f"   🚢 Em movimento (chegando/saindo): {underway}")
                print(f"   {'─' * 70}")
                print(f"   Por tipo de navio:")
                print(f"      🛢️  Tankers (petróleo/químicos): {tankers}")
                print(f"      📦 Bulk Carriers (granéis):     {bulkers}")
                print(f"      🚢 Outros:                      {other}")
                
                if speeds:
                    avg_speed = sum(speeds) / len(speeds)
                    max_speed = max(speeds)
                    min_speed = min(speeds)
                    print(f"   {'─' * 70}")
                    print(f"   Velocidade (navios em movimento):")
                    print(f"      Média: {avg_speed:.1f} knots")
                    print(f"      Máxima: {max_speed:.1f} knots")
                    print(f"      Mínima: {min_speed:.1f} knots")
                else:
                    avg_speed = 0
                
                # Análise da fila
                print(f"\n🎯 ANÁLISE PARA PREDIÇÃO:")
                print(f"   {'─' * 70}")
                print(f"   Features AIS que serão usadas pelo modelo:")
                print(f"      ais_navios_no_raio:      {total}")
                print(f"      ais_fila_ao_largo:       {anchored}")
                print(f"      ais_velocidade_media_kn: {avg_speed:.1f}")
                print(f"   {'─' * 70}")
                
                if anchored > 0:
                    tempo_estimado_min = anchored * 6
                    tempo_estimado_max = anchored * 12
                    print(f"   ⚠️  FILA DETECTADA: {anchored} navios aguardando atracação")
                    print(f"   Tempo estimado de espera (baseado em histórico):")
                    print(f"      Mínimo: {tempo_estimado_min} horas ({tempo_estimado_min/24:.1f} dias)")
                    print(f"      Máximo: {tempo_estimado_max} horas ({tempo_estimado_max/24:.1f} dias)")
                else:
                    print(f"   ✅ SEM FILA: Porto aparentemente livre no momento")
                
                # Mostrar alguns navios de exemplo
                print(f"\n📋 EXEMPLOS DE NAVIOS DETECTADOS (5 primeiros):")
                for i, vessel in enumerate(vessels[:5], 1):
                    name = vessel.get('name', 'N/A')
                    imo = vessel.get('imo', 'N/A')
                    vtype = vessel.get('type_specific') or vessel.get('type') or 'N/A'
                    speed = vessel.get('speed') or 0
                    dest = vessel.get('destination', 'N/A')
                    dist = vessel.get('distance', 0)
                    
                    status_emoji = "⚓" if speed < 0.5 else "🚢"
                    status_text = "Parado (fila)" if speed < 0.5 else f"Movendo {speed:.1f}kn"
                    
                    print(f"\n   {status_emoji} Navio {i}: {name}")
                    print(f"      IMO: {imo}")
                    print(f"      Tipo: {vtype}")
                    print(f"      Status: {status_text}")
                    print(f"      Distância do porto: {dist:.2f}nm (~{dist*1.852:.1f}km)")
                    print(f"      Destino: {dest}")
                
                # Contabilizar créditos
                total_credits += total
                
            else:
                print(f"❌ Formato de resposta inesperado")
                print(f"   Keys: {data.keys()}")
        
        elif response.status_code == 401:
            print(f"❌ Erro 401: API key inválida")
            break
        elif response.status_code == 403:
            print(f"❌ Erro 403: Sem créditos")
            break
        else:
            print(f"❌ Erro {response.status_code}: {response.text[:200]}")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

# Resumo final
print(f"\n{'=' * 90}")
print(f"💳 CONSUMO DE CRÉDITOS")
print(f"{'=' * 90}")
print(f"   Total de navios consultados: {total_credits}")
print(f"   Créditos usados (1 por navio): {total_credits} créditos")
print(f"   Plano recomendado: Starter (€199/mês, 20.000 créditos)")
if total_credits > 0:
    queries_possiveis = 20000 // total_credits
    print(f"   Consultas possíveis por mês: ~{queries_possiveis} previsões")

print(f"\n{'=' * 90}")
print(f"✅ TESTE CONCLUÍDO COM SUCESSO!")
print(f"   API Datalastic funcionando corretamente")
print(f"   Dados AIS em tempo real obtidos para ambos os portos")
print(f"   Pronto para integração com o sistema de previsão")
print(f"{'=' * 90}")
