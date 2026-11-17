import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import re
import math
import io
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard Culligan - Reclame Aqui",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS PERSONALIZADO (SEM CABEÇALHO) ---
st.markdown("""
<style>
    /* --- REMOVER CABEÇALHO PADRÃO DO STREAMLIT --- */
    [data-testid="stHeader"] {
        display: none;
    }
    [data-testid="stToolbar"] {
        visibility: hidden;
    }
    
    /* Ajuste para o conteúdo colar no topo */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Animação */
    @keyframes gradient-animation {
        0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; }
    }
    
    .status-card {
        border-radius: 12px; padding: 8px; color: white; text-align: center; height: 110px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15); background-size: 200% 200%;
        animation: gradient-animation 6s ease infinite; margin-bottom: 5px;
    }
    .neutral-card {
        background-color: white; border-radius: 12px; padding: 8px; color: #333; text-align: center;
        height: 110px; display: flex; flex-direction: column; justify-content: center; align-items: center;
        box-shadow: 0 3px 6px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; margin-bottom: 5px;
    }
    .grad-ra1000 { background-image: linear-gradient(45deg, #0d462b, #11b841, #0d462b); }
    .grad-otimo { background-image: linear-gradient(45deg, #11b841, #52c41a, #11b841); }
    .grad-bom { background-image: linear-gradient(45deg, #0050b3, #1890ff, #0050b3); }
    .grad-regular { background-image: linear-gradient(45deg, #faad14, #ffc53d, #faad14); color: #333 !important; }
    .grad-ruim { background-image: linear-gradient(45deg, #fa541c, #ff7a45, #fa541c); }
    .grad-nao-rec { background-image: linear-gradient(45deg, #cf1322, #f5222d, #cf1322); }
    .grad-neutro { background-image: linear-gradient(45deg, #595959, #8c8c8c, #595959); }
    
    .card-title { font-size: 0.85rem; font-weight: 600; margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px; }
    .card-value { font-size: 1.8rem; font-weight: 800; line-height: 1.1; margin: 0; }
    .card-sub { font-size: 0.7rem; opacity: 0.9; margin-top: 2px; }
    
    .kpi-container {
        background-color: white; border-radius: 10px; padding: 10px; border: 1px solid #e0e0e0;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.05); text-align: center; height: 100%;
    }
    .kpi-title { font-size: 0.8rem; color: #666; font-weight: 600; margin-bottom: 4px; }
    .kpi-value { font-size: 1.4rem; color: #333; font-weight: 700; margin: 0; }
    .kpi-meta { font-size: 0.65rem; color: #888; background: #f5f5f5; padding: 1px 6px; border-radius: 8px; display: inline-block; margin-bottom: 3px;}
    
    .explanation-box {
        background-color: #f8f9fa; border-left: 4px solid #0050b3; padding: 8px 12px;
        border-radius: 4px; margin-bottom: 10px; font-size: 0.85rem; line-height: 1.3;
    }
    .custom-title-container {
        display: flex; justify-content: space-between; align-items: center; 
        margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px;
    }
    .custom-title { font-size: 1.5rem; font-weight: 700; color: #333; margin: 0; }
    .custom-date { font-size: 0.8rem; color: #999; margin: 0; }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES ---

MESES_PT = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
            7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}

# Paletas validadas (colorblind-safe) para os gráficos das visões de operador e notas
COR_STATUS_HUGME = {'Novo': '#d03b3b', 'Pendente': '#eda100', 'Respondido': '#2a78d6', 'Fechado': '#008300'}
ORDEM_STATUS_HUGME = ['Novo', 'Pendente', 'Respondido', 'Fechado']

ORDEM_FAIXAS_AGING = ['0-7 dias', '8-15 dias', '16-30 dias', 'Acima de 30 dias']
COR_FAIXA_AGING = {'0-7 dias': '#86b6ef', '8-15 dias': '#3987e5', '16-30 dias': '#1c5cab', 'Acima de 30 dias': '#0d366b'}

ORDEM_GRUPOS_NOTA = ['Críticas (0-5)', 'Neutras (6-7)', 'Promotoras (8-10)']
COR_GRUPO_NOTA = {'Críticas (0-5)': '#d03b3b', 'Neutras (6-7)': '#eda100', 'Promotoras (8-10)': '#008300'}

CORES_OPERADORES = ['#2a78d6', '#008300', '#e87ba4', '#eda100', '#1baf7a', '#eb6834', '#4a3aa7', '#e34948']

# --- FUNÇÕES ---

def formatar_mes(periodo):
    return f"{MESES_PT[periodo.month]}/{periodo.year}"

def grupo_nota(nota):
    if nota <= 5: return 'Críticas (0-5)'
    elif nota <= 7: return 'Neutras (6-7)'
    return 'Promotoras (8-10)'

def estilizar_grafico(fig, altura=340):
    fig.update_layout(
        height=altura, plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(t=30, b=10, l=10, r=10),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0, title=None),
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color='#333'),
    )
    fig.update_xaxes(gridcolor='#e1e0d9', zerolinecolor='#c3c2b7', linecolor='#c3c2b7')
    fig.update_yaxes(gridcolor='#e1e0d9', zerolinecolor='#c3c2b7', linecolor='#c3c2b7')
    return fig

@st.cache_data
def converter_para_excel(df):
    """Converte um DataFrame Pandas para um arquivo Excel em memória."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return buffer.getvalue()

def arredondar_ra(valor):
    decimal, inteiro = math.modf(valor)
    if decimal >= 0.5: return math.ceil(valor)
    else: return math.floor(valor)

def get_periodos_ra(df):
    if df is None or df.empty: return None, None, None, None
    hoje = datetime.now().date()
    max_base = df['Data Reclamação'].max().date()
    data_ref = max_base if max_base < (hoje - timedelta(days=30)) else hoje
    primeiro_dia_atual = data_ref.replace(day=1)
    fim_oficial = primeiro_dia_atual - timedelta(days=1)
    inicio_oficial = (fim_oficial + relativedelta(day=1)) - relativedelta(months=5)
    inicio_previa = inicio_oficial + relativedelta(months=1)
    fim_previa = data_ref 
    return inicio_oficial, fim_oficial, inicio_previa, fim_previa

def calcular_indicadores(df_input):
    total_reclamacoes = len(df_input)
    qtd_nao_respondidas = len(df_input[df_input['Status RA'] == 'NÃO RESPONDIDO'])
    respondidas = total_reclamacoes - qtd_nao_respondidas
    ir = (respondidas / total_reclamacoes) * 100 if total_reclamacoes > 0 else 0
    df_avaliadas = df_input.dropna(subset=['Nota'])
    total_avaliadas = len(df_avaliadas)
    soma_notas = df_avaliadas['Nota'].sum()
    ma = soma_notas / total_avaliadas if total_avaliadas > 0 else 0
    solucionadas = len(df_avaliadas[df_avaliadas['Seu problema foi resolvido?'] == 'SIM'])
    is_val = (solucionadas / total_avaliadas) * 100 if total_avaliadas > 0 else 0
    voltaria = len(df_avaliadas[df_avaliadas['Voltaria a fazer negócio?'] == 'SIM'])
    in_val = (voltaria / total_avaliadas) * 100 if total_avaliadas > 0 else 0
    ar = ((ir * 2) + (ma * 10 * 3) + (is_val * 3) + (in_val * 2)) / 100
    
    tempo_medio = 0
    if 'Data de Resposta' in df_input.columns and 'Data Reclamação' in df_input.columns:
        df_resp = df_input.dropna(subset=['Data de Resposta']).copy()
        if not df_resp.empty:
            df_resp['Dias'] = (df_resp['Data de Resposta'] - df_resp['Data Reclamação']).dt.days
            tempo_medio = df_resp['Dias'].mean()

    return {
        'total_reclamacoes': total_reclamacoes, 'respondidas': respondidas, 'nao_respondidas': qtd_nao_respondidas, 
        'total_avaliadas': total_avaliadas, 'IR': ir, 'MA': ma, 'IS': is_val, 'IN': in_val, 'AR': ar,
        'Tempo_Medio': tempo_medio
    }

def definir_status_final(kpis, ignorar_volume=False):
    ir, ar, total, ma = kpis['IR'], kpis['AR'], kpis['total_avaliadas'], kpis['MA']
    is_val, in_val = kpis['IS'], kpis['IN']
    emoji_ra1000, emoji_otimo, emoji_bom = "🏆", "😄", "🙂"
    emoji_regular, emoji_ruim, emoji_nao_rec, emoji_sem_rep = "😐", "😟", "😡", "😶"

    if not ignorar_volume and total < 10: return "Sem Reputação", "grad-neutro", "Menos de 10 avaliações", emoji_sem_rep
    if ir < 50: return "NÃO RECOMENDADA", "grad-nao-rec", "Índice de Resposta < 50%", emoji_nao_rec
    criterios_ra1000 = (ir >= 90 and is_val >= 90 and in_val >= 70 and ma >= 7 and ar >= 8)
    volume_ok_ra1000 = True if ignorar_volume else (total >= 50)
    if criterios_ra1000 and volume_ok_ra1000: return "RA1000", "grad-ra1000", "Selo RA1000 Conquistado", emoji_ra1000
    if ar >= 8: return "ÓTIMO", "grad-otimo", "", emoji_otimo
    elif ar >= 7: return "BOM", "grad-bom", "", emoji_bom
    elif ar >= 6: return "REGULAR", "grad-regular", "", emoji_regular
    elif ar >= 5: return "RUIM", "grad-ruim", "", emoji_ruim
    else: return "NÃO RECOMENDADA", "grad-nao-rec", "Score AR < 5.0", emoji_nao_rec

def processar_qualitativo(df_quali):
    df_f = df_quali[df_quali['Status RA'].str.upper().str.contains('AVALIADO', na=False)].copy()
    if len(df_f) == 0: return None
    def categorizar(nota):
        if pd.isna(nota): return "S/ Nota"
        if nota <= 5: return "Notas Críticas (de 1 à 5)"
        elif nota <= 7: return "Notas Neutras (de 6 à 7)"
        else: return "Notas Promotoras (de 8 à 10)"
    df_f['Categoria Nota'] = df_f['Nota'].apply(categorizar)
    return df_f

def gerar_tabela_mensal(df):
    df['Mes_Ano'] = df['Data Reclamação'].dt.to_period('M')
    resultados = []
    for periodo, dados_mes in df.groupby('Mes_Ano'):
        kpis = calcular_indicadores(dados_mes)
        status, _, _, emoji = definir_status_final(kpis, ignorar_volume=True)
        nome_mes = f"{MESES_PT[periodo.month]} {periodo.year}"
        selo_display = f"{emoji} {status}" if status != "Sem Reputação" else status
        resultados.append({
            'Referência': periodo, 'Mês': nome_mes, 'Selo': selo_display,
            'IS (Meta ≥ 90%)': kpis['IS'], 'IN (Meta ≥ 70%)': kpis['IN'], 
            'IR (Meta ≥ 90%)': kpis['IR'], 'MA (Meta ≥ 7)': kpis['MA'], 
            'AR (Meta ≥ 8)': kpis['AR'], 'Avaliações': kpis['total_avaliadas'], 'Volumetria': kpis['total_reclamacoes']
        })
    if not resultados: return pd.DataFrame()
    return pd.DataFrame(resultados).sort_values('Referência', ascending=True)

def colorir_tabela(val):
    val_str = str(val).upper().strip()
    if 'RA1000' in val_str: return 'background-color: #0d462b; color: white; font-weight: bold; text-align: center;' 
    elif 'ÓTIMO' in val_str: return 'background-color: #11b841; color: white; font-weight: bold; text-align: center;'
    elif 'BOM' in val_str: return 'background-color: #0066cc; color: white; font-weight: bold; text-align: center;'
    elif 'REGULAR' in val_str: return 'background-color: #ffcc33; color: black; font-weight: bold; text-align: center;'
    elif 'RUIM' in val_str: return 'background-color: #ff9933; color: white; font-weight: bold; text-align: center;'
    elif 'NÃO RECOMENDADA' in val_str: return 'background-color: #ff3333; color: white; font-weight: bold; text-align: center;'
    elif 'SEM REPUTAÇÃO' in val_str: return 'background-color: #9e9e9e; color: white; font-weight: bold; text-align: center;'
    return 'color: black; text-align: center;'

def colorir_ir(val):
    try:
        v = float(str(val).replace('%',''))
        if v < 50: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
    except: pass
    return ''

def converter_data_avaliacao(valor):
    """A coluna 'Data Avaliacao' vem mista do HugMe: parte datetime, parte número serial do Excel."""
    if pd.isna(valor): return pd.NaT
    if isinstance(valor, (int, float)):
        return pd.Timestamp('1899-12-30') + pd.Timedelta(days=float(valor))
    return pd.to_datetime(valor, errors='coerce')

# --- PADRONIZAÇÃO DE FRANQUIAS: Matriz (visão unificada) > Franquia > Regional ---
# A visão unificada vem de Matriz_Franquias.xlsx, extraído do cadastro de Prestador de Serviço
# (Franquia -> Matriz -> Nome no dashboard). Franquia fora do arquivo = grupo próprio.
ARQ_MATRIZES = 'Matriz_Franquias.xlsx'
# Códigos antigos que aparecem na Base Eco mas não estão no De-Para.xlsx
CODIGOS_EXTRAS = {'FRQ_ECO_SP_SÃO_PAULO_2': 'FRQ_ECOHOUSE SÃO PAULO_2', 'FRQ_ECO_SP_ZONA_NORTE_2': 'FRQ_ECO_SP_Z_NORTE_2'}
SEM_FRANQUIA = 'Sem franquia'
SEM_REGIONAL = ''  # regional não identificada fica em branco (não aparece no mapa nem nas tabelas)
_RE_REGIONAL = re.compile(r'\s+(R\d+(?:\s*-\s*MATRIZ)?)\s*$')

def _sem_regional(nome):
    return _RE_REGIONAL.sub('', str(nome).strip()).strip()

def _regional(nome):
    m = _RE_REGIONAL.search(str(nome).strip())
    return re.sub(r'\s*-\s*', ' - ', m.group(1)) if m else None

@st.cache_data
def carregar_de_para():
    """Código antigo (Franquia Range CEP) -> franquia nova sem regional, a partir do De-Para.xlsx."""
    if not os.path.exists('De-Para.xlsx'): return {}
    dp = pd.read_excel('De-Para.xlsx', dtype=str).dropna()
    dp.columns = ['codigo', 'novo'][:len(dp.columns)] + list(dp.columns[2:])
    mapa = {}
    for cod, novo in zip(dp['codigo'], dp['novo']):
        mapa[cod.strip().upper()] = _sem_regional(novo).upper()
    for cod, alvo in CODIGOS_EXTRAS.items():
        if alvo.upper() in mapa: mapa[cod.upper()] = mapa[alvo.upper()]
    return mapa

@st.cache_data
def carregar_matrizes():
    """Franquia (sem regional) -> nome do grupo no dashboard, a partir do Matriz_Franquias.xlsx."""
    if not os.path.exists(ARQ_MATRIZES): return {}
    mt = pd.read_excel(ARQ_MATRIZES, dtype=str)
    mapa = {}
    for fr, nome in zip(mt['Franquia'], mt['Nome no dashboard']):
        if isinstance(fr, str) and fr.strip():
            mapa[fr.strip().upper()] = nome.strip() if isinstance(nome, str) and nome.strip() else fr.strip().upper()
    return mapa

@st.cache_data
def carregar_regional_por_ticket():
    """Franquia e regional reais por ticket (Salesforce / aprovados), arquivo sem dados pessoais."""
    arq = 'Franquia_Regional_por_ticket.xlsx'
    if not os.path.exists(arq): return pd.DataFrame(columns=['Id HugMe', 'Franquia', 'Regional', 'Fonte'])
    reg = pd.read_excel(arq, dtype={'Franquia': str, 'Regional': str, 'Fonte': str})
    reg['Franquia'] = reg['Franquia'].str.strip().str.upper()
    return reg

def padronizar_franquias(df):
    """Cria Franquia Unificada / Franquia / Regional e deixa 'Franquias' sem a regional.
    Aceita o que vier da tag do HugMe: código antigo (FRQ_ECO_...), nome novo com regional
    (FRQ GALEAO SUL RJ R02) ou nome novo sem regional (FRQ OSASCO SP)."""
    de_para = carregar_de_para()
    unif = carregar_matrizes()
    reg = carregar_regional_por_ticket()
    reg_por_id = {}
    for r in reg.itertuples(index=False):
        reg_por_id.setdefault(r[0], []).append((r[1], r[2] if isinstance(r[2], str) else None, r[3]))

    def ler_tag(valor):
        if pd.isna(valor) or not str(valor).strip() or str(valor).strip() in ('NÃO INFORMADO', 'NAN'): return None, None
        v = re.split(r'\s*[;,]\s*', str(valor).strip())[0].strip().upper()  # se vierem 2 tags, vale a primeira
        if v in de_para: return de_para[v], None
        return _sem_regional(v), _regional(v)

    fr, rg, un, fonte = [], [], [], []
    ids = df['Id HugMe'] if 'Id HugMe' in df.columns else pd.Series([None] * len(df), index=df.index)
    for valor, hid in zip(df['Franquias'], ids):
        f, r = ler_tag(valor)
        origem = 'Tag do HugMe' if r else None
        cand = reg_por_id.get(hid, [])
        if f is None:
            # tag vazia: só usa o que foi aprovado na planilha de sugestões
            aprov = [c for c in cand if c[2].startswith('Aprovado')]
            if aprov: f, r, origem = aprov[0][0], aprov[0][1], 'Aprovado (sugestões)'
        elif r is None and cand:
            # tag sem regional: detalha pelo Salesforce, desde que fique no mesmo grupo unificado
            grupo = unif.get(f, f)
            mesmos = [c for c in cand if unif.get(c[0], c[0]) == grupo]
            if len(mesmos) == 1:
                f, r, origem = mesmos[0][0], mesmos[0][1], 'Salesforce (CPF)'
        fr.append(f if f else SEM_FRANQUIA)
        rg.append(r if r else SEM_REGIONAL)
        un.append(unif.get(f, f) if f else SEM_FRANQUIA)
        fonte.append(origem or ('Tag do HugMe (sem regional)' if f else '-'))

    df['Franquia (tag original)'] = df['Franquias']
    df['Franquia Unificada'] = un
    df['Franquia'] = fr
    df['Regional'] = rg
    df['Franquia + Regional'] = [f if r == SEM_REGIONAL or f == SEM_FRANQUIA else f'{f} {r}' for f, r in zip(fr, rg)]
    df['Origem da regional'] = fonte
    # 'Franquias' passa a ser a franquia padronizada (sem regional) em todas as abas
    df['Franquias'] = [pd.NA if f == SEM_FRANQUIA else f for f in fr]
    return df

def agregar_franquias(df_in, colunas):
    return df_in.groupby(colunas).agg(
        Volume=('ID Reclame Aqui', 'count'), Nota_Media=('Nota', 'mean'),
        Resolvido_Pct=('Seu problema foi resolvido?', lambda x: (x == 'SIM').mean() * 100),
        Voltaria_Pct=('Voltaria a fazer negócio?', lambda x: (x == 'SIM').mean() * 100)
    ).reset_index()

def mapa_rede(df_in, titulo="Clique numa matriz para abrir as franquias e regionais"):
    base = df_in[df_in['Franquia Unificada'] != SEM_FRANQUIA]
    if base.empty: return None
    # montado nó a nó: a franquia mostra o total; regional só aparece quando identificada
    # (o que não tem regional fica como espaço da própria franquia, sem rótulo)
    ids, labels, parents, values, colors = ['Rede'], ['Rede'], [''], [len(base)], ['#f4f6f8']
    paleta = px.colors.qualitative.Safe
    for i, (m, g_m) in enumerate(sorted(base.groupby('Franquia Unificada'), key=lambda x: -len(x[1]))):
        cor = paleta[i % len(paleta)]
        id_m = f'Rede/{m}'
        ids.append(id_m); labels.append(m); parents.append('Rede'); values.append(len(g_m)); colors.append(cor)
        for f, g_f in g_m.groupby('Franquia'):
            id_f = f'{id_m}/{f}'
            ids.append(id_f); labels.append(f); parents.append(id_m); values.append(len(g_f)); colors.append(cor)
            for r, g_r in g_f[g_f['Regional'] != SEM_REGIONAL].groupby('Regional'):
                ids.append(f'{id_f}/{r}'); labels.append(r); parents.append(id_f); values.append(len(g_r)); colors.append(cor)
    fig = go.Figure(go.Treemap(ids=ids, labels=labels, parents=parents, values=values, branchvalues='total',
                               marker=dict(colors=colors), textinfo='label+value+percent root',
                               hovertemplate='<b>%{label}</b><br>Volume: %{value}<br>% da rede: %{percentRoot:.1%}<extra></extra>'))
    fig.update_layout(title=titulo, height=520, margin=dict(t=50, l=5, r=5, b=5))
    return fig

# --- MEMÓRIA DE TAGS DO HUGME ---
# Em 12/11/2026 as tags antigas de franquia, marca e cancelamento foram removidas dos tickets no HugMe,
# e a exportação passou a vir com essas colunas vazias. Memoria_Tags_HugMe.xlsx guarda, por Id HugMe,
# o último valor conhecido (sem dados pessoais) e completa só o que vier vazio na Base Eco.
ARQ_MEMORIA = 'Memoria_Tags_HugMe.xlsx'
COLS_MEMORIA = ['Franquias', 'cancelamento', 'Marca']
_RE_TAG_FRANQUIA = re.compile(r'^(FRQ|AT)[ _]', re.IGNORECASE)

@st.cache_data
def carregar_memoria_tags():
    if not os.path.exists(ARQ_MEMORIA): return pd.DataFrame()
    mem = pd.read_excel(ARQ_MEMORIA, dtype={c: str for c in COLS_MEMORIA + ['Tag de franquia original']})
    mem['Id HugMe'] = pd.to_numeric(mem['Id HugMe'], errors='coerce').astype('Int64')
    return mem.dropna(subset=['Id HugMe']).drop_duplicates('Id HugMe', keep='last').set_index('Id HugMe')

def _vazio(serie):
    txt = serie.astype(str).str.strip().str.upper()
    return serie.isna() | txt.isin(['', 'NAN', 'NONE', 'NÃO INFORMADO'])

def _franquia_nas_tags(tags):
    """Se a tag de franquia vier na coluna Tags (outra categoria no HugMe), pega a primeira."""
    if pd.isna(tags): return None
    for t in re.split(r'\s*;\s*', str(tags)):
        if _RE_TAG_FRANQUIA.match(t.strip()): return t.strip()
    return None

def completar_com_memoria(df):
    """Completa Franquias / cancelamento / Marca vazios: 1º pela coluna Tags, 2º pela memória (Id HugMe)."""
    for col in COLS_MEMORIA:
        df[col] = df[col].astype(object) if col in df.columns else pd.Series([pd.NA] * len(df), index=df.index, dtype=object)
    vazio = _vazio(df['Franquias'])
    if 'Tags' in df.columns:
        achadas = df.loc[vazio, 'Tags'].map(_franquia_nas_tags)
        df.loc[achadas.dropna().index, 'Franquias'] = achadas.dropna()
    df['Franquia pela memória'] = 'Não'
    mem = carregar_memoria_tags()
    if mem.empty or 'Id HugMe' not in df.columns: return df
    ids = df['Id HugMe'].astype('Int64')
    for col in COLS_MEMORIA:
        if col not in mem.columns: continue
        vazio = _vazio(df[col])
        valores = ids[vazio].map(mem[col]).dropna()
        df.loc[valores.index, col] = valores
        if col == 'Franquias': df.loc[valores.index, 'Franquia pela memória'] = 'Sim'
    return df

def memoria_atualizada(df):
    """Memória atual + tags que vieram nesta Base Eco (o valor da exportação vence)."""
    mem = carregar_memoria_tags()
    mem = mem.reset_index() if not mem.empty else pd.DataFrame(columns=['Id HugMe'])
    novo = pd.DataFrame({
        'Id HugMe': df['Id HugMe'].astype('Int64'), 'Data Reclamação': df['Data Reclamação'],
        'Franquias': [f if (m == 'Não' and isinstance(t, str) and isinstance(f, str)) else pd.NA
                      for f, t, m in zip(df['Franquias'], df['Franquia (tag original)'], df['Franquia pela memória'])],
        'Tag de franquia original': [t if (m == 'Não' and isinstance(t, str)) else pd.NA for t, m in zip(df['Franquia (tag original)'], df['Franquia pela memória'])],
        'cancelamento': df['cancelamento'], 'Marca': df['Marca'],
        'Capturado da base de': datetime.now().strftime('%d/%m/%Y')})
    novo = novo[novo[COLS_MEMORIA].notna().any(axis=1)]
    junto = pd.concat([mem, novo], ignore_index=True)
    # por ticket: fica o último valor não vazio de cada coluna
    final = junto.groupby('Id HugMe', sort=False).agg(lambda x: x.dropna().iloc[-1] if x.notna().any() else pd.NA).reset_index()
    return final.sort_values('Data Reclamação')

@st.cache_data
def carregar_dados():
    file_path = 'BaseEco.xlsx'
    if not os.path.exists(file_path): return None
    df = pd.read_excel(file_path)
    df = completar_com_memoria(df)
    df['Data Reclamação'] = pd.to_datetime(df['Data Reclamação'])
    if 'Data de Resposta' in df.columns:
        # também vem como número serial do Excel no HugMe (antes virava 1970 e o tempo médio dava negativo)
        df['Data de Resposta'] = df['Data de Resposta'].map(converter_data_avaliacao)
    if 'Data Avaliacao' in df.columns:
        df['Data Avaliacao'] = df['Data Avaliacao'].map(converter_data_avaliacao)
    if 'Status Hugme' in df.columns:
        df['Status Hugme'] = df['Status Hugme'].fillna('Não informado').astype(str).str.strip().str.capitalize()
    if 'Atribuido Para' in df.columns:
        df['Atribuido Para'] = df['Atribuido Para'].fillna('Não atribuído').astype(str).str.strip()
    cols_str = ['Status RA', 'Seu problema foi resolvido?', 'Voltaria a fazer negócio?', 'Motivos Ecohouse', 'Franquias', 'Origem', 'Marca']
    for col in cols_str:
        if col in df.columns: df[col] = df[col].astype(str).str.strip().str.upper()
        else:
            if col in ['Motivos Ecohouse', 'Franquias']: df[col] = "NÃO INFORMADO"
    df = df.replace('NAN', pd.NA)
    df = padronizar_franquias(df)
    df = aplicar_classificacao(df)
    return df

def renderizar_painel_principal(df_painel, titulo_secao):
    if len(df_painel) == 0:
        st.warning(f"Sem dados disponíveis para: {titulo_secao}")
        return None

    kpis = calcular_indicadores(df_painel)
    status_txt, status_class, status_obs, status_emoji = definir_status_final(kpis, ignorar_volume=False)

    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        st.markdown(f"""<div class="status-card {status_class}"><div class="card-title">{titulo_secao}</div><div class="card-value">{status_emoji} {status_txt}</div><div class="card-sub">{status_obs}</div></div>""", unsafe_allow_html=True)
    with c2:
        cor_map = {"grad-ra1000": "#0d462b", "grad-otimo": "#11b841", "grad-bom": "#0050b3", "grad-regular": "#faad14", "grad-ruim": "#fa541c", "grad-nao-rec": "#cf1322", "grad-neutro": "#595959"}
        cor_texto = cor_map.get(status_class, "#333")
        st.markdown(f"""<div class="neutral-card" style="border: 2px solid {cor_texto};"><div class="card-title" style="color: #666;">Score AR [Meta ≥ 8]</div><div class="card-value" style="color: {cor_texto};">{kpis['AR']:.1f}</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="neutral-card" style="background-color: #f8f9fa;"><div class="card-title" style="color: #666;">Volume Total</div><div class="card-value" style="color: #333;">{kpis['total_reclamacoes']}</div><div class="card-sub">Reclamações no período</div></div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    META_IR, META_MA, META_IS, META_IN = 90.0, 7.0, 90.0, 70.0
    def criar_kpi_card(titulo, valor, meta, is_percent=True, help_text=""):
        delta = valor - meta
        cor_delta = "green" if delta >= 0 else "red"
        sinal = "+" if delta > 0 else ""
        fmt_val = f"{valor:.1f}%" if is_percent else f"{valor:.2f}"
        fmt_delta = f"{sinal}{delta:.1f}" + ("%" if is_percent else "")
        return f"""<div class="kpi-container" title="{help_text}"><div class="kpi-meta">Meta: {meta}{'%' if is_percent else ''}</div><div class="kpi-title">{titulo}</div><div class="kpi-value">{fmt_val}</div><div style="color: {cor_delta}; font-weight: bold; font-size: 0.9rem;">{fmt_delta}</div></div>"""

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.markdown(criar_kpi_card("Resposta (IR)", kpis['IR'], META_IR, True, f"{kpis['respondidas']} respondidas"), unsafe_allow_html=True)
    with m2: st.markdown(criar_kpi_card("Nota (MA)", kpis['MA'], META_MA, False, f"{kpis['total_avaliadas']} avaliações"), unsafe_allow_html=True)
    with m3: st.markdown(criar_kpi_card("Solução (IS)", kpis['IS'], META_IS, True), unsafe_allow_html=True)
    with m4: st.markdown(criar_kpi_card("Voltaria (IN)", kpis['IN'], META_IN, True), unsafe_allow_html=True)
    with m5: 
        st.markdown(f"""<div class="kpi-container"><div class="kpi-meta">Tempo de Resposta</div><div class="kpi-title">Média (Dias)</div><div class="kpi-value" style="color: #666;">{kpis['Tempo_Medio']:.1f}</div><div style="font-size: 0.8em; color: #999;">Dias Corridos</div></div>""", unsafe_allow_html=True)
    
    return kpis

# --- APP PRINCIPAL ---
# ===================== MOTIVOS RA: CATEGORIA E SUBCATEGORIA (leitura caso a caso) =====================
# A classificação não vem do HugMe: fica no arquivo Classificacao_Motivos_RA.xlsx (sem dados pessoais),
# atualizado toda semana com os casos novos. O dash cruza pelo Id HugMe.
ARQ_CLASSIFICACAO = 'Classificacao_Motivos_RA.xlsx'
AGUARDANDO = 'Aguardando classificação'
ORDEM_CATEGORIAS = ['Cancelamento', 'Financeiro', 'Campo', 'Supply', 'Processo e sistemas', 'Atendimento', 'Produto', 'Comercial', 'Outros']
# cor fixa por categoria (não muda com filtro); "aguardando" fica em cinza
COR_CATEGORIA = {'Cancelamento': '#2a78d6', 'Financeiro': '#eb6834', 'Campo': '#1baf7a', 'Supply': '#8a5a2b', 'Processo e sistemas': '#eda100',
                 'Atendimento': '#e87ba4', 'Produto': '#008300', 'Comercial': '#6250d6', 'Outros': '#e34948', AGUARDANDO: '#b5b4ad'}
COLS_CLASSIF = {'Categoria': 'Categoria Motivo', 'Subcategoria': 'Subcategoria Motivo', 'Categoria secundária': 'Categoria Secundária',
                'Tipo de serviço (campo)': 'Serviço de Campo', 'Motivo de origem (cancelamento)': 'Origem do Cancelamento',
                'Já tinha cancelado?': 'Já Tinha Cancelado'}
COLS_LISTA_MOTIVOS = ['Id HugMe', 'ID Reclame Aqui', 'Data Reclamação', 'Título', 'Franquia Unificada', 'Franquia',
                      'Categoria Motivo', 'Subcategoria Motivo', 'Categoria Secundária', 'Serviço de Campo', 'Origem do Cancelamento',
                      'Já Tinha Cancelado', 'Status RA', 'Nota', 'Seu problema foi resolvido?', 'Voltaria a fazer negócio?']
FMT_MOTIVOS = {'% do total': '{:.1f}%', '% na categoria': '{:.1f}%', 'Nota média': '{:.2f}', '% Resolvido': '{:.1f}%', '% Voltaria': '{:.1f}%', '%': '{:.0f}%'}

@st.cache_data
def carregar_classificacao():
    if not os.path.exists(ARQ_CLASSIFICACAO): return None
    cl = pd.read_excel(ARQ_CLASSIFICACAO, sheet_name='Classificação')
    cl['Id HugMe'] = pd.to_numeric(cl['Id HugMe'], errors='coerce').astype('Int64')
    cl = cl.dropna(subset=['Id HugMe']).drop_duplicates('Id HugMe', keep='last')
    return cl

def aplicar_classificacao(df):
    df = df.drop(columns=[c for c in COLS_CLASSIF.values() if c in df.columns])
    cl = carregar_classificacao()
    if cl is None:
        for c in COLS_CLASSIF.values(): df[c] = pd.NA
    else:
        mapa = cl.set_index('Id HugMe')
        ids = pd.to_numeric(df['Id HugMe'], errors='coerce').astype('Int64')
        for origem, destino in COLS_CLASSIF.items():
            df[destino] = ids.map(mapa[origem]).values if origem in mapa.columns else pd.NA
    df['Categoria Motivo'] = df['Categoria Motivo'].fillna(AGUARDANDO)
    df['Subcategoria Motivo'] = df['Subcategoria Motivo'].fillna(AGUARDANDO)
    return df

def ultima_leitura_classificacao():
    cl = carregar_classificacao()
    if cl is None or 'Classificado em' not in cl.columns: return ''
    datas = pd.to_datetime(cl['Classificado em'].astype(str), dayfirst=True, errors='coerce')
    return datas.max().strftime('%d/%m/%Y') if datas.notna().any() else ''

def _fmt_motivos(tabela):
    return tabela.style.format({k: v for k, v in FMT_MOTIVOS.items() if k in tabela.columns}, na_rep='-')

def _resumo_motivos(df_in, colunas):
    out = df_in.groupby(colunas).size().rename('Volume').to_frame()
    av = df_in.dropna(subset=['Nota'])
    ga = av.groupby(colunas)
    out['Avaliadas'] = ga.size()
    out['Nota média'] = ga['Nota'].mean()
    out['% Resolvido'] = ga['Seu problema foi resolvido?'].apply(lambda x: (x == 'SIM').mean() * 100)
    out['% Voltaria'] = ga['Voltaria a fazer negócio?'].apply(lambda x: (x == 'SIM').mean() * 100)
    out['Avaliadas'] = out['Avaliadas'].fillna(0).astype(int)
    return out.reset_index()

def _contagem(serie, nome):
    vc = serie.value_counts()
    return pd.DataFrame({nome: vc.index, 'Qtd': vc.values, '%': vc.values / max(vc.sum(), 1) * 100})

def _semana_seg(datas):
    d = datas.dt.normalize()
    return (d - pd.to_timedelta(d.dt.weekday, unit='D')).dt.date

def _rotulo_semana(seg):
    return f"{seg:%d/%m}–{(seg + timedelta(days=6)):%d/%m}"

def excel_varias_abas(abas):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for nome, tabela in abas.items():
            aba = nome[:31]
            tabela.to_excel(writer, index=False, sheet_name=aba)
            ws = writer.sheets[aba]
            for col in ws.columns:
                maior = max((len(str(c.value)) for c in col if c.value is not None), default=8)
                ws.column_dimensions[col[0].column_letter].width = min(60, max(10, maior + 2))
            ws.freeze_panes = 'A2'
    return buffer.getvalue()

def _barras_horizontais(tabela, col_y, cor=None, col_cor=None, altura=340):
    fig = px.bar(tabela, x='Volume', y=col_y, orientation='h', text='Rótulo',
                 color=col_cor, color_discrete_map=COR_CATEGORIA if col_cor else None)
    fig.update_traces(textposition='outside', textfont_color='#333', cliponaxis=False,
                      hovertemplate='%{y}<br>%{x} reclamações<extra></extra>')
    if cor: fig.update_traces(marker_color=cor)
    fig.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending', 'title': None}, xaxis_title=None, bargap=0.35)
    fig.update_xaxes(range=[0, tabela['Volume'].max() * 1.25])
    fig = estilizar_grafico(fig, altura)
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)
    return fig

def renderizar_motivos_ra(df):
    st.subheader("🗂️ Motivos RA: categoria e subcategoria")
    if carregar_classificacao() is None:
        st.warning(f"Arquivo `{ARQ_CLASSIFICACAO}` não encontrado na pasta do dash: todas as reclamações aparecem como '{AGUARDANDO}'.")
    ult = ultima_leitura_classificacao()
    st.markdown("<div class='explanation-box'><b>📌 Como ler esta aba</b><br>"
                "Cada reclamação foi lida (título e texto) e recebeu <b>1 categoria e 1 subcategoria</b>: o que o cliente precisa que seja resolvido. "
                "Quando ele relata outro problema junto, ele entra na <b>categoria secundária</b>. A classificação não usa a tag de motivo da operação."
                + (f"<br><i>Última leitura: {ult}. O que entrou na Base Eco depois disso aparece como <b>{AGUARDANDO}</b>.</i>" if ult else "")
                + "</div>", unsafe_allow_html=True)

    # ---------- período ----------
    hoje = datetime.now().date()
    seg_atual = hoje - timedelta(days=hoje.weekday())
    ini_of, fim_of, ini_pv, fim_pv = get_periodos_ra(df)
    d_min, d_max = df['Data Reclamação'].min().date(), df['Data Reclamação'].max().date()
    periodos = {
        'Todo o período': (d_min, d_max),
        'Janela oficial (6 meses fechados)': (ini_of, fim_of),
        'Prévia (próxima reputação)': (ini_pv, fim_pv),
        'Mês atual': (hoje.replace(day=1), hoje),
        'Últimas 4 semanas fechadas': (seg_atual - timedelta(days=28), seg_atual - timedelta(days=1)),
        'Última semana fechada (seg a dom)': (seg_atual - timedelta(days=7), seg_atual - timedelta(days=1)),
        'Semana atual': (seg_atual, hoje),
        'Personalizado': None,
    }
    c_p1, c_p2, c_p3 = st.columns([2, 1, 1])
    escolha = c_p1.selectbox("📅 Período:", list(periodos), key='mot_periodo')
    if periodos[escolha] is None:
        ini = c_p2.date_input("Início", d_min, key='mot_ini')
        fim = c_p3.date_input("Fim", d_max, key='mot_fim')
    else:
        ini, fim = periodos[escolha]
        c_p2.markdown(f"<div style='padding-top: 34px; color: #52514e;'>{ini:%d/%m/%Y} a {fim:%d/%m/%Y}</div>", unsafe_allow_html=True)
    dfp = df[(df['Data Reclamação'].dt.date >= ini) & (df['Data Reclamação'].dt.date <= fim)].copy()
    if dfp.empty:
        st.info("Sem reclamações no período selecionado.")
        return

    total = len(dfp)
    n_aguard = int((dfp['Categoria Motivo'] == AGUARDANDO).sum())
    dcl = dfp[dfp['Categoria Motivo'] != AGUARDANDO]
    res_cat = _resumo_motivos(dfp, ['Categoria Motivo']).sort_values('Volume', ascending=False)
    res_cat['% do total'] = res_cat['Volume'] / total * 100
    ordem = res_cat.loc[res_cat['Categoria Motivo'] != AGUARDANDO, 'Categoria Motivo'].tolist()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Reclamações no período", f"{total}")
    k2.metric("Classificadas", f"{len(dcl)}", f"{len(dcl) / total * 100:.0f}% do período", delta_color='off')
    if ordem:
        top = res_cat[res_cat['Categoria Motivo'] == ordem[0]].iloc[0]
        k3.metric("Maior categoria", ordem[0], f"{top['% do total']:.0f}% das reclamações", delta_color='off')
    k4.metric(AGUARDANDO, f"{n_aguard}")
    if n_aguard:
        st.warning(f"⏳ {n_aguard} reclamação(ões) deste período ainda não foram lidas. Elas entram na próxima classificação semanal.")
    area_download = st.container()
    abas_relatorio = {}

    # ---------- 1. categorias ----------
    st.markdown("---")
    st.markdown("### 1. Categorias")
    c1, c2 = st.columns([1, 1.25])
    with c1:
        graf = res_cat.copy()
        graf['Rótulo'] = graf['Volume'].astype(str) + ' (' + graf['% do total'].round(0).astype(int).astype(str) + '%)'
        st.plotly_chart(_barras_horizontais(graf, 'Categoria Motivo', col_cor='Categoria Motivo', altura=max(280, 40 * len(graf) + 60)),
                        use_container_width=True)
    with c2:
        tab_cat = res_cat[['Categoria Motivo', 'Volume', '% do total', 'Avaliadas', 'Nota média', '% Resolvido', '% Voltaria']]
        st.dataframe(_fmt_motivos(tab_cat), use_container_width=True, hide_index=True)
        st.caption("Nota média, % resolvido e % voltaria consideram só as reclamações que o cliente já avaliou.")
    abas_relatorio['Categorias'] = tab_cat

    # ---------- 2. quebra ----------
    st.markdown("---")
    st.markdown("### 2. Quebra das categorias")
    res_sub = pd.DataFrame()
    if dcl.empty:
        st.info("Nenhuma reclamação classificada neste período.")
    else:
        res_sub = _resumo_motivos(dcl, ['Categoria Motivo', 'Subcategoria Motivo'])
        res_sub['% na categoria'] = res_sub['Volume'] / res_sub.groupby('Categoria Motivo')['Volume'].transform('sum') * 100
        res_sub['% do total'] = res_sub['Volume'] / total * 100
        res_sub['_o'] = res_sub['Categoria Motivo'].map({c: i for i, c in enumerate(ordem)})
        res_sub = res_sub.sort_values(['_o', 'Volume'], ascending=[True, False]).drop(columns='_o')
        res_sub = res_sub[['Categoria Motivo', 'Subcategoria Motivo', 'Volume', '% na categoria', '% do total', 'Avaliadas', 'Nota média', '% Resolvido', '% Voltaria']]

        cat_sel = st.selectbox("🔎 Abrir a categoria:", ordem, key='mot_cat')
        sub_sel = res_sub[res_sub['Categoria Motivo'] == cat_sel].copy()
        base_cat = dcl[dcl['Categoria Motivo'] == cat_sel]
        c3, c4 = st.columns([1.5, 1])
        with c3:
            sub_sel['Rótulo'] = sub_sel['Volume'].astype(str) + ' (' + sub_sel['% na categoria'].round(0).astype(int).astype(str) + '%)'
            st.plotly_chart(_barras_horizontais(sub_sel, 'Subcategoria Motivo', cor=COR_CATEGORIA.get(cat_sel, '#2a78d6'),
                                                altura=max(240, 44 * len(sub_sel) + 60)), use_container_width=True)
            st.dataframe(_fmt_motivos(sub_sel.drop(columns=['Rótulo', 'Categoria Motivo'])), use_container_width=True, hide_index=True)
        with c4:
            if cat_sel == 'Cancelamento':
                st.markdown("##### O que levou o cliente a querer cancelar")
                st.dataframe(_fmt_motivos(_contagem(base_cat['Origem do Cancelamento'].fillna('Não informa'), 'Origem')),
                             use_container_width=True, hide_index=True)
            if cat_sel == 'Campo':
                st.markdown("##### Tipo de serviço")
                st.dataframe(_fmt_motivos(_contagem(base_cat['Serviço de Campo'].fillna('Não informado'), 'Serviço')),
                             use_container_width=True, hide_index=True)
            st.markdown("##### O que mais o cliente relata")
            st.dataframe(_fmt_motivos(_contagem(base_cat['Categoria Secundária'].fillna('Só esse problema'), 'Também relata')),
                         use_container_width=True, hide_index=True)

        with st.expander("📋 Quebra completa (todas as categorias e subcategorias)", expanded=False):
            st.dataframe(_fmt_motivos(res_sub), use_container_width=True, hide_index=True, height=420)
            st.download_button("📥 Baixar quebra completa (XLSX)", data=converter_para_excel(res_sub), file_name='quebra_motivos_ra.xlsx',
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_mot_quebra')

        # quem já tinha cancelado o contrato quando reclamou (fica nas categorias do problema: cobrança, retirada, estorno)
        ja = dcl[dcl['Já Tinha Cancelado'].astype(str).str.strip().str.upper() == 'SIM'] if 'Já Tinha Cancelado' in dcl.columns else dcl.iloc[0:0]
        st.markdown("#### Quem já tinha cancelado o contrato quando reclamou")
        cj1, cj2 = st.columns([1, 2.5])
        cj1.metric("Já tinham cancelado", f"{len(ja)}", f"{len(ja) / max(len(dcl), 1) * 100:.0f}% das classificadas", delta_color='off')
        cj1.caption("Esses clientes não estão em Cancelamento: entram no problema que trouxeram depois de cancelar (cobrança, retirada, estorno).")
        if not ja.empty:
            tj = ja.groupby(['Categoria Motivo', 'Subcategoria Motivo']).size().rename('Qtd').reset_index().sort_values('Qtd', ascending=False)
            tj['%'] = tj['Qtd'] / len(ja) * 100
            cj2.dataframe(_fmt_motivos(tj), use_container_width=True, hide_index=True)
    abas_relatorio['Subcategorias'] = res_sub

    # ---------- 3. evolução semanal ----------
    st.markdown("---")
    st.markdown("### 3. Evolução semanal")
    n_sem = st.slider("Quantas semanas mostrar (seg a dom, até a semana atual):", 4, 26, 12, key='mot_semanas')
    semanas = [seg_atual - timedelta(weeks=i) for i in range(n_sem - 1, -1, -1)]
    dfs = df.assign(Semana=_semana_seg(df['Data Reclamação']))
    dfs = dfs[(dfs['Semana'] >= semanas[0]) & (dfs['Semana'] <= seg_atual)]
    rotulos = [_rotulo_semana(s) + (' *' if s == seg_atual else '') for s in semanas]
    piv = (dfs.groupby(['Categoria Motivo', 'Semana']).size().unstack(fill_value=0)
              .reindex(columns=semanas, fill_value=0))
    cats_ev = [c for c in ORDEM_CATEGORIAS + [AGUARDANDO] if c in piv.index] + [c for c in piv.index if c not in ORDEM_CATEGORIAS + [AGUARDANDO]]
    piv = piv.reindex(cats_ev)
    fig_ev = go.Figure()
    for cat in cats_ev:
        fig_ev.add_trace(go.Bar(x=rotulos, y=piv.loc[cat].values, name=cat, marker_color=COR_CATEGORIA.get(cat, '#8a8985'),
                                marker_line=dict(color='white', width=2), hovertemplate=f'{cat}<br>%{{x}}: %{{y}}<extra></extra>'))
    fig_ev.update_layout(barmode='stack', xaxis_title=None, yaxis_title=None, bargap=0.3)
    fig_ev = estilizar_grafico(fig_ev, 400)
    fig_ev.update_layout(legend_traceorder='normal')
    fig_ev.update_xaxes(automargin=True)
    fig_ev.update_yaxes(automargin=True)
    st.plotly_chart(fig_ev, use_container_width=True)

    tab_ev = piv.copy()
    tab_ev.columns = rotulos
    tab_ev.loc['Total'] = tab_ev.sum()
    if n_sem >= 3:
        tab_ev['Δ últ. semana fechada'] = tab_ev[rotulos[-2]] - tab_ev[rotulos[-3]]
        delta = tab_ev.drop(index=['Total', AGUARDANDO], errors='ignore')['Δ últ. semana fechada']
        if not delta.empty and delta.max() > 0:
            st.caption(f"Na última semana fechada ({rotulos[-2]}), a maior alta foi em **{delta.idxmax()}** "
                       f"(+{int(delta.max())} contra a semana anterior).")
    tab_ev = tab_ev.reset_index().rename(columns={'index': 'Categoria Motivo', 'Categoria Motivo': 'Categoria Motivo'})
    st.dataframe(tab_ev, use_container_width=True, hide_index=True)
    st.caption("* semana atual, ainda em andamento. Esta visão não depende do período escolhido no topo.")
    abas_relatorio['Evolução semanal'] = tab_ev

    with st.expander("📈 Evolução semanal das subcategorias", expanded=False):
        cats_disp = [c for c in ORDEM_CATEGORIAS if c in dfs['Categoria Motivo'].unique()]
        if cats_disp:
            cat_ev = st.selectbox("Categoria:", cats_disp, key='mot_ev_cat')
            piv_sub = (dfs[dfs['Categoria Motivo'] == cat_ev].groupby(['Subcategoria Motivo', 'Semana']).size()
                       .unstack(fill_value=0).reindex(columns=semanas, fill_value=0))
            piv_sub.columns = rotulos
            piv_sub['Total'] = piv_sub.sum(axis=1)
            st.dataframe(piv_sub.sort_values('Total', ascending=False).reset_index(), use_container_width=True, hide_index=True)
        else:
            st.info("Sem reclamações classificadas nessas semanas.")

    # ---------- 4. franquias por motivo ----------
    st.markdown("---")
    st.markdown("### 4. Franquias por motivo")
    TODAS_CAT = 'Todas as categorias'
    cc1, cc2, cc3 = st.columns([1.2, 1.5, 1.3])
    cat_fr = cc1.selectbox("Categoria:", [TODAS_CAT] + ordem, key='mot_fr_cat')
    niveis_fr = {'Matriz (visão unificada)': 'Franquia Unificada', 'Franquia': 'Franquias', 'Franquia + Regional': 'Franquia + Regional'}
    niveis_fr = {k: v for k, v in niveis_fr.items() if v in dcl.columns}
    nivel = cc2.radio("Agrupar por:", list(niveis_fr), horizontal=True, key='mot_fr_nivel')
    col_f = niveis_fr[nivel]
    incluir_sec = False
    if cat_fr != TODAS_CAT:
        incluir_sec = cc3.checkbox(f"Incluir quando {cat_fr} é a categoria secundária", key='mot_fr_sec',
                                   help="Ex.: cobrança de um cliente que também está sem visita, ou problema que terminou em pedido de cancelamento.")
    if cat_fr == TODAS_CAT:
        base_fr = dcl.copy()
        base_fr['Coluna'] = base_fr['Categoria Motivo']
    else:
        eh_cat = dcl['Categoria Motivo'] == cat_fr
        if incluir_sec:
            eh_cat = eh_cat | (dcl['Categoria Secundária'] == cat_fr)
        base_fr = dcl[eh_cat].copy()
        base_fr['Coluna'] = base_fr['Subcategoria Motivo'].where(base_fr['Categoria Motivo'] == cat_fr, f'{cat_fr} como secundária')
    piv_c = pd.DataFrame()
    if base_fr.empty:
        st.info("Nenhuma reclamação nesse filtro no período.")
    else:
        sem_fr = int((base_fr['Franquia Unificada'] == SEM_FRANQUIA).sum())
        bc = base_fr[base_fr['Franquia Unificada'] != SEM_FRANQUIA]
        if not bc.empty:
            piv_c = bc.groupby([col_f, 'Coluna']).size().unstack(fill_value=0)
            piv_c = piv_c[piv_c.sum().sort_values(ascending=False).index]
            piv_c.insert(0, 'Total', piv_c.sum(axis=1))
            ind = _resumo_motivos(bc, [col_f]).set_index(col_f)[['Avaliadas', 'Nota média', '% Resolvido', '% Voltaria']]
            piv_c = piv_c.join(ind).sort_values('Total', ascending=False).reset_index()
            st.dataframe(_fmt_motivos(piv_c).background_gradient(subset=['Total'], cmap='Reds'), use_container_width=True, hide_index=True, height=420)
            st.download_button("📥 Baixar Franquias por motivo (XLSX)", data=converter_para_excel(piv_c), file_name='franquias_por_motivo.xlsx',
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_mot_campo')
        st.caption(f"{len(base_fr)} reclamações no filtro"
                   + (f"; {sem_fr} sem franquia identificada ficam fora da tabela. " if sem_fr else ". ")
                   + "Colunas do meio: quantidade por " + ("categoria" if cat_fr == TODAS_CAT else "subcategoria")
                   + ". Nota média, % resolvido e % voltaria consideram só as avaliadas.")
    abas_relatorio['Franquias x Motivo'] = piv_c

    # ---------- 5. casos ----------
    st.markdown("---")
    st.markdown("### 5. Casos do período")
    f1, f2 = st.columns(2)
    cats_f = f1.multiselect("Categoria:", ordem + ([AGUARDANDO] if n_aguard else []), key='mot_f_cat')
    base_l = dfp[dfp['Categoria Motivo'].isin(cats_f)] if cats_f else dfp
    subs_f = f2.multiselect("Subcategoria:", sorted(base_l['Subcategoria Motivo'].dropna().astype(str).unique()), key='mot_f_sub')
    if subs_f:
        base_l = base_l[base_l['Subcategoria Motivo'].isin(subs_f)]
    cols_l = [c for c in COLS_LISTA_MOTIVOS if c in base_l.columns]
    lista = base_l[cols_l].sort_values('Data Reclamação', ascending=False)
    st.dataframe(lista, use_container_width=True, hide_index=True, height=380)
    st.download_button("📥 Baixar casos filtrados (XLSX)", data=converter_para_excel(lista), file_name='casos_motivos_ra.xlsx',
                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_mot_casos')
    abas_relatorio['Casos'] = dfp[[c for c in COLS_LISTA_MOTIVOS if c in dfp.columns]].sort_values('Data Reclamação', ascending=False)

    # ---------- relatório do período (fica no topo da aba) ----------
    resumo = pd.DataFrame({'Item': ['Período', 'Reclamações', 'Classificadas', AGUARDANDO, 'Última leitura', 'Gerado em'],
                           'Valor': [f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y}", total, len(dcl), n_aguard, ult or '-', datetime.now().strftime('%d/%m/%Y %H:%M')]})
    with area_download:
        st.download_button("📥 Baixar relatório do período (XLSX: categorias, quebra, semanas, franquias e casos)",
                           data=excel_varias_abas({'Resumo': resumo, **abas_relatorio}),
                           file_name=f"motivos_ra_{ini:%d-%m-%Y}_a_{fim:%d-%m-%Y}.xlsx",
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_mot_relatorio')

def main():
    df = carregar_dados()
    if df is None:
        st.error("Erro: Arquivo `BaseEco.xlsx` não encontrado.")
        return

    c_head1, c_head2 = st.columns([4, 1])
    with c_head1: st.markdown("""<div class="custom-title-container"><h1 class="custom-title">📊 Reclame Aqui - Culligan</h1></div>""", unsafe_allow_html=True)
    with c_head2:
        hoje_str = datetime.now().strftime('%d/%m/%Y')
        st.markdown(f"<div style='text-align: right; padding-top: 15px; color: #888; font-size: 0.8rem;'>📅 {hoje_str}</div>", unsafe_allow_html=True)

    ini_oficial, fim_oficial, ini_previa, fim_previa = get_periodos_ra(df)
    n_memoria = int((df['Franquia pela memória'] == 'Sim').sum())
    if n_memoria:
        st.caption(f"🧠 {n_memoria} tickets vieram sem tag de franquia na Base Eco e foram completados pela memória de tags. "
                   f"{int((df['Franquia Unificada'] == SEM_FRANQUIA).sum())} seguem sem franquia. Detalhes na aba 📂 Base Completa.")

    tab_oficial, tab_previa, tab_mensal, tab_operador, tab_notas, tab_franquias, tab_motivos, tab_quali, tab_simulador, tab_avancada, tab_dados = st.tabs([
        "🔒 Visão Oficial", "⚡ Visão Prévia", "📅 Evolução Mensal", "👥 Visão por Operador", "⭐ Visão de Notas",
        "🏢 Análise por Franquia", "🗂️ Motivos RA", "🔍 Análise Qualitativa",
        "🎯 Simulador de Metas", "🔐 Análises Avançadas", "📂 Base Completa"
    ])

    with tab_oficial:
        st.markdown(f"<div class='explanation-box'><b>📌 Como funciona a Visão Oficial?</b><br>Cálculo baseado nos <b>últimos 6 meses fechados</b> (excluindo mês atual). Esta é a reputação pública exibida no site do RA.<br><i>Período: {ini_oficial.strftime('%d/%m/%Y')} a {fim_oficial.strftime('%d/%m/%Y')}</i></div>", unsafe_allow_html=True)
        mask = (df['Data Reclamação'].dt.date >= ini_oficial) & (df['Data Reclamação'].dt.date <= fim_oficial)
        renderizar_painel_principal(df.loc[mask], "Reputação Oficial")

    with tab_previa:
        st.markdown(f"<div class='explanation-box'><b>📌 Como funciona a Visão Prévia?</b><br>Janela deslizante: remove o mês mais antigo da oficial e adiciona o <b>mês atual (vigente)</b>. Simula a reputação futura imediata.<br><i>Período: {ini_previa.strftime('%d/%m/%Y')} a {fim_previa.strftime('%d/%m/%Y')}</i></div>", unsafe_allow_html=True)
        mask_prev = (df['Data Reclamação'].dt.date >= ini_previa) & (df['Data Reclamação'].dt.date <= fim_previa)
        df_prev = df.loc[mask_prev]
        st.session_state['kpis_previa'] = renderizar_painel_principal(df_prev, "Visão Prévia")

    with tab_mensal:
        st.subheader("📅 Tabela de Evolução Mensal")
        st.markdown("<div class='explanation-box' style='border-left-color: #52c41a;'><b>ℹ️ Entenda a Métrica desta Aba:</b><br>Esta visão é <b>Gerencial</b>. Ignoramos a regra de volume mínimo (50 avaliações) do RA. Se o mês tiver indicadores de qualidade RA1000 (IS≥90, IR≥90, etc.), ele receberá o selo na tabela, independente do volume.</div>", unsafe_allow_html=True)
        
        min_date = df['Data Reclamação'].min().date()
        max_date = df['Data Reclamação'].max().date()
        c_evo1, c_evo2 = st.columns(2)
        d_evo_ini = c_evo1.date_input("Início", min_date, min_value=min_date, max_value=max_date)
        d_evo_fim = c_evo2.date_input("Fim", max_date, min_value=min_date, max_value=max_date)
        
        mask_evo = (df['Data Reclamação'].dt.date >= d_evo_ini) & (df['Data Reclamação'].dt.date <= d_evo_fim)
        df_evo = df.loc[mask_evo].copy()
        
        if not df_evo.empty:
            tabela_final = gerar_tabela_mensal(df_evo)
            if not tabela_final.empty:
                display_cols = ['Mês', 'Selo', 'IS (Meta ≥ 90%)', 'IN (Meta ≥ 70%)', 'IR (Meta ≥ 90%)', 'MA (Meta ≥ 7)', 'AR (Meta ≥ 8)', 'Avaliações', 'Volumetria']
                tabela_display = tabela_final[display_cols]
                st.dataframe(tabela_display.style.map(colorir_tabela, subset=['Selo']).map(colorir_ir, subset=['IR (Meta ≥ 90%)']).format({'IS (Meta ≥ 90%)': '{:.1f}%', 'IN (Meta ≥ 70%)': '{:.1f}%', 'IR (Meta ≥ 90%)': '{:.1f}%', 'MA (Meta ≥ 7)': '{:.2f}', 'AR (Meta ≥ 8)': '{:.1f}'}), use_container_width=True, height=500)
                
                # --- BOTÃO DOWNLOAD: Evolução Mensal ---
                st.download_button(
                    label="📥 Baixar Evolução Mensal (XLSX)",
                    data=converter_para_excel(tabela_display),
                    file_name='evolucao_mensal.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else: st.warning("Sem dados processáveis.")
        else: st.info("Sem dados no período.")

    # --- ABA VISÃO POR OPERADOR ---
    with tab_operador:
        st.subheader("👥 Visão por Operador")
        st.markdown("""<div class='explanation-box'><b>📌 Legenda do Status Hugme:</b><br>
        🔴 <b>Novo</b> = sem resposta pública &nbsp;|&nbsp; 🟡 <b>Pendente</b> = cliente postou réplica &nbsp;|&nbsp;
        🔵 <b>Respondido</b> = respondido no público &nbsp;|&nbsp; 🟢 <b>Fechado</b> = cliente avaliou</div>""", unsafe_allow_html=True)

        min_d_op = df['Data Reclamação'].min().date()
        max_d_op = df['Data Reclamação'].max().date()
        operadores_todos = sorted(df['Atribuido Para'].dropna().unique().tolist())
        mapa_cores_op = {op: CORES_OPERADORES[i % len(CORES_OPERADORES)] for i, op in enumerate(operadores_todos)}

        c_op1, c_op2, c_op3 = st.columns([1, 1, 2])
        d_op_ini = c_op1.date_input("Início", min_d_op, min_value=min_d_op, max_value=max_d_op, key="op_ini")
        d_op_fim = c_op2.date_input("Fim", max_d_op, min_value=min_d_op, max_value=max_d_op, key="op_fim")
        ops_sel = c_op3.multiselect("👤 Operadores (vazio = todos):", operadores_todos, key="op_sel")

        mask_op = (df['Data Reclamação'].dt.date >= d_op_ini) & (df['Data Reclamação'].dt.date <= d_op_fim)
        df_op = df.loc[mask_op].copy()
        if ops_sel: df_op = df_op[df_op['Atribuido Para'].isin(ops_sel)]

        if df_op.empty:
            st.info("Sem dados para o filtro selecionado.")
        else:
            # --- 1. CARGA DE CASOS POR OPERADOR ---
            st.markdown("### 📋 Casos Atribuídos por Operador")
            pivot_status = df_op.pivot_table(index='Atribuido Para', columns='Status Hugme',
                                             values='ID Reclame Aqui', aggfunc='count', fill_value=0)
            for st_col in ORDEM_STATUS_HUGME:
                if st_col not in pivot_status.columns: pivot_status[st_col] = 0
            resumo_op = pd.DataFrame({'Casos Atribuídos': df_op.groupby('Atribuido Para').size()})
            resumo_op = resumo_op.join(pivot_status[ORDEM_STATUS_HUGME])
            resumo_op['% Sem Resposta'] = (resumo_op['Novo'] / resumo_op['Casos Atribuídos']) * 100
            resumo_op = resumo_op.sort_values('Casos Atribuídos', ascending=False).reset_index()
            resumo_op = resumo_op.rename(columns={
                'Novo': 'Novo (Sem Resposta Pública)', 'Pendente': 'Pendente (Réplica)',
                'Respondido': 'Respondido (Público)', 'Fechado': 'Fechado (Avaliado)'})

            c_t1, c_t2 = st.columns([1.2, 1])
            with c_t1:
                st.dataframe(resumo_op.style
                             .background_gradient(subset=['Casos Atribuídos'], cmap='Blues')
                             .map(lambda v: 'background-color: #fdecea; color: #c62828; font-weight: bold;' if isinstance(v, (int, float)) and v > 0 else '', subset=['Novo (Sem Resposta Pública)'])
                             .format({'% Sem Resposta': '{:.1f}%'}),
                             use_container_width=True, hide_index=True)
                st.download_button(label="📥 Baixar Resumo por Operador (XLSX)", data=converter_para_excel(resumo_op),
                                   file_name='resumo_operadores.xlsx',
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key="dl_op_resumo")
            with c_t2:
                df_status_plot = df_op.groupby(['Atribuido Para', 'Status Hugme']).size().reset_index(name='Casos')
                fig_st = px.bar(df_status_plot, y='Atribuido Para', x='Casos', color='Status Hugme', orientation='h',
                                text='Casos', color_discrete_map=COR_STATUS_HUGME,
                                category_orders={'Status Hugme': ORDEM_STATUS_HUGME})
                fig_st.update_traces(marker_line_color='white', marker_line_width=2, textposition='inside', textangle=0)
                fig_st.update_layout(barmode='stack', yaxis={'categoryorder': 'total ascending', 'title': None}, xaxis={'title': 'Casos'},
                                     uniformtext_minsize=10, uniformtext_mode='hide')
                st.plotly_chart(estilizar_grafico(fig_st), use_container_width=True)

            # --- 2. AGING DOS CASOS SEM RESPOSTA PÚBLICA ---
            st.markdown("---")
            st.markdown("### ⏳ Aging dos Casos Sem Resposta Pública (Status: Novo)")
            hoje_ref = pd.Timestamp.now().normalize()
            df_novo = df_op[df_op['Status Hugme'] == 'Novo'].copy()

            if df_novo.empty:
                st.success("🎉 Nenhum caso sem resposta pública no filtro atual!")
            else:
                df_novo['Aging (dias)'] = (hoje_ref - df_novo['Data Reclamação'].dt.normalize()).dt.days
                df_novo['Faixa de Aging'] = pd.cut(df_novo['Aging (dias)'], bins=[-1, 7, 15, 30, 10**6], labels=ORDEM_FAIXAS_AGING)

                acima_30 = int((df_novo['Aging (dias)'] > 30).sum())
                k_ag1, k_ag2, k_ag3, k_ag4 = st.columns(4)
                k_ag1.markdown(f"""<div class="kpi-container"><div class="kpi-title">Casos Sem Resposta</div><div class="kpi-value" style="color: #c62828;">{len(df_novo)}</div></div>""", unsafe_allow_html=True)
                k_ag2.markdown(f"""<div class="kpi-container"><div class="kpi-title">Aging Médio</div><div class="kpi-value">{df_novo['Aging (dias)'].mean():.0f} dias</div></div>""", unsafe_allow_html=True)
                k_ag3.markdown(f"""<div class="kpi-container"><div class="kpi-title">Caso Mais Antigo</div><div class="kpi-value">{df_novo['Aging (dias)'].max():.0f} dias</div></div>""", unsafe_allow_html=True)
                k_ag4.markdown(f"""<div class="kpi-container"><div class="kpi-title">Acima de 30 Dias</div><div class="kpi-value" style="color: {'#c62828' if acima_30 > 0 else '#2e7d32'};">{acima_30}</div></div>""", unsafe_allow_html=True)
                st.caption(f"Aging calculado em dias corridos até hoje ({hoje_ref.strftime('%d/%m/%Y')}).")

                c_ag1, c_ag2 = st.columns(2)
                with c_ag1:
                    st.markdown("##### 📊 Aging por Operador")
                    agg_aging = df_novo.groupby(['Atribuido Para', 'Faixa de Aging'], observed=True).size().reset_index(name='Casos')
                    fig_ag = px.bar(agg_aging, y='Atribuido Para', x='Casos', color='Faixa de Aging', orientation='h',
                                    text='Casos', color_discrete_map=COR_FAIXA_AGING,
                                    category_orders={'Faixa de Aging': ORDEM_FAIXAS_AGING})
                    fig_ag.update_traces(marker_line_color='white', marker_line_width=2, textposition='inside', textangle=0)
                    fig_ag.update_layout(barmode='stack', yaxis={'categoryorder': 'total ascending', 'title': None}, xaxis={'title': 'Casos'},
                                         uniformtext_minsize=10, uniformtext_mode='hide')
                    st.plotly_chart(estilizar_grafico(fig_ag), use_container_width=True)
                with c_ag2:
                    st.markdown("##### 🚨 Motivos dos Casos Sem Resposta")
                    top_mot_novo = df_novo['Categoria Motivo'].value_counts().reset_index()
                    top_mot_novo.columns = ['Motivo', 'Casos']
                    fig_mot = px.bar(top_mot_novo.head(8), x='Casos', y='Motivo', orientation='h', text='Casos')
                    fig_mot.update_traces(marker_color='#2a78d6', marker_line_color='white', marker_line_width=2, textposition='outside')
                    fig_mot.update_layout(yaxis={'categoryorder': 'total ascending', 'title': None}, xaxis={'title': 'Casos'}, showlegend=False)
                    st.plotly_chart(estilizar_grafico(fig_mot), use_container_width=True)

                st.markdown("##### 📋 Detalhamento: Caso a Caso (com Motivo e Franquia)")
                cols_detalhe = ['Atribuido Para', 'ID Reclame Aqui', 'Título', 'Data Reclamação',
                                'Aging (dias)', 'Faixa de Aging', 'Categoria Motivo', 'Subcategoria Motivo', 'Franquia Unificada', 'Franquias', 'Regional']
                cols_detalhe = [c for c in cols_detalhe if c in df_novo.columns]
                df_detalhe = df_novo[cols_detalhe].sort_values('Aging (dias)', ascending=False)

                def destacar_aging(row):
                    estilo = 'background-color: #fdecea;' if row['Aging (dias)'] > 30 else ''
                    return [estilo] * len(row)
                st.dataframe(df_detalhe.style.apply(destacar_aging, axis=1).format({'Data Reclamação': '{:%d/%m/%Y}'}),
                             use_container_width=True, hide_index=True)
                st.download_button(label="📥 Baixar Casos Sem Resposta (XLSX)", data=converter_para_excel(df_detalhe),
                                   file_name='casos_sem_resposta_publica.xlsx',
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key="dl_op_aging")

            # --- 3. NOTAS POR OPERADOR ---
            st.markdown("---")
            st.markdown("### ⭐ Notas por Operador")
            st.caption("Baseado na **Data de Avaliação** (quando o cliente avaliou), não na data da reclamação. "
                       "O filtro de operadores acima se aplica; o filtro de datas não (use o seletor de mês abaixo).")

            df_aval = df[df['Nota'].notna() & df['Data Avaliacao'].notna()].copy()
            if ops_sel: df_aval = df_aval[df_aval['Atribuido Para'].isin(ops_sel)]

            if df_aval.empty:
                st.info("Sem avaliações para o filtro selecionado.")
            else:
                df_aval['Mes_Aval'] = df_aval['Data Avaliacao'].dt.to_period('M')
                meses_disp = sorted(df_aval['Mes_Aval'].unique(), reverse=True)
                mes_sel = st.selectbox("📅 Mês de referência:", meses_disp, format_func=formatar_mes, key="op_mes")

                df_mes_aval = df_aval[df_aval['Mes_Aval'] == mes_sel]
                st.markdown(f"##### 📆 Detalhe do Mês: {formatar_mes(mes_sel)}")
                if df_mes_aval.empty:
                    st.info("Sem avaliações neste mês.")
                else:
                    resumo_notas = df_mes_aval.groupby('Atribuido Para').agg(
                        Avaliações=('Nota', 'count'),
                        Nota_Média=('Nota', 'mean'),
                        Notas_0_5=('Nota', lambda x: int((x <= 5).sum())),
                        Notas_6_7=('Nota', lambda x: int(x.between(6, 7).sum())),
                        Notas_8_10=('Nota', lambda x: int((x >= 8).sum())),
                        Resolvido_Sim=('Seu problema foi resolvido?', lambda x: int((x == 'SIM').sum())),
                        Voltaria_Sim=('Voltaria a fazer negócio?', lambda x: int((x == 'SIM').sum())),
                    ).reset_index().sort_values('Avaliações', ascending=False)
                    resumo_notas['% Resolvido'] = resumo_notas['Resolvido_Sim'] / resumo_notas['Avaliações'] * 100
                    resumo_notas['% Voltaria'] = resumo_notas['Voltaria_Sim'] / resumo_notas['Avaliações'] * 100
                    resumo_notas = resumo_notas.rename(columns={
                        'Nota_Média': 'Nota Média', 'Notas_0_5': 'Notas 0-5', 'Notas_6_7': 'Notas 6-7',
                        'Notas_8_10': 'Notas 8-10', 'Resolvido_Sim': 'Problema Resolvido (Sim)', 'Voltaria_Sim': 'Voltaria Negócio (Sim)'})
                    st.dataframe(resumo_notas.style
                                 .background_gradient(subset=['Nota Média'], cmap='RdYlGn', vmin=0, vmax=10)
                                 .format({'Nota Média': '{:.2f}', '% Resolvido': '{:.0f}%', '% Voltaria': '{:.0f}%'}),
                                 use_container_width=True, hide_index=True)
                    st.download_button(label="📥 Baixar Notas do Mês (XLSX)", data=converter_para_excel(resumo_notas),
                                       file_name=f'notas_operadores_{mes_sel}.xlsx',
                                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key="dl_op_notas_mes")

                st.markdown(f"##### 📈 Histórico dos Últimos 6 Meses (até {formatar_mes(mes_sel)})")
                df_hist = df_aval[(df_aval['Mes_Aval'] >= mes_sel - 5) & (df_aval['Mes_Aval'] <= mes_sel)].copy()
                hist = df_hist.groupby(['Atribuido Para', 'Mes_Aval']).agg(
                    Qtd=('Nota', 'count'),
                    Media=('Nota', 'mean'),
                    ResolvidoPct=('Seu problema foi resolvido?', lambda x: (x == 'SIM').mean() * 100),
                    VoltariaPct=('Voltaria a fazer negócio?', lambda x: (x == 'SIM').mean() * 100),
                ).reset_index()

                opcoes_metrica = {
                    'Nota Média': ('Media', '{:.2f}'),
                    'Qtd de Avaliações': ('Qtd', '{:.0f}'),
                    '% Problema Resolvido': ('ResolvidoPct', '{:.0f}%'),
                    '% Voltaria a Fazer Negócio': ('VoltariaPct', '{:.0f}%'),
                }
                metrica_sel = st.radio("Métrica:", list(opcoes_metrica.keys()), horizontal=True, key="op_metrica")
                col_metrica, fmt_metrica = opcoes_metrica[metrica_sel]

                hist = hist.sort_values('Mes_Aval')
                hist['Mês'] = hist['Mes_Aval'].map(formatar_mes)
                ordem_meses_hist = [formatar_mes(p) for p in sorted(hist['Mes_Aval'].unique())]

                fig_hist = px.line(hist, x='Mês', y=col_metrica, color='Atribuido Para', markers=True,
                                   color_discrete_map=mapa_cores_op, category_orders={'Mês': ordem_meses_hist})
                fig_hist.update_traces(line_width=2, marker_size=8)
                fig_hist.update_layout(yaxis={'title': metrica_sel}, xaxis={'title': None})
                if '%' in metrica_sel: fig_hist.update_yaxes(range=[0, 105])
                st.plotly_chart(estilizar_grafico(fig_hist, altura=380), use_container_width=True)

                pivot_hist = hist.pivot_table(index='Atribuido Para', columns='Mês', values=col_metrica)
                pivot_hist = pivot_hist[[m for m in ordem_meses_hist if m in pivot_hist.columns]]
                pivot_display = pivot_hist.copy()
                for c in pivot_display.columns:
                    pivot_display[c] = pivot_display[c].map(lambda v: '-' if pd.isna(v) else fmt_metrica.format(v))
                pivot_display = pivot_display.reset_index()
                pivot_hist = pivot_hist.reset_index()
                st.dataframe(pivot_display, use_container_width=True, hide_index=True)
                st.download_button(label="📥 Baixar Histórico 6 Meses (XLSX)", data=converter_para_excel(pivot_hist),
                                   file_name='historico_notas_operadores.xlsx',
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key="dl_op_hist")

    # --- ABA VISÃO DE NOTAS ---
    with tab_notas:
        st.subheader("⭐ Visão de Notas (Avaliações Recebidas)")
        st.markdown("""<div class='explanation-box'><b>📌 Como funciona esta visão?</b><br>
        Mostra as notas recebidas por mês, com base na <b>Data de Avaliação</b> (quando o cliente avaliou no RA).
        Grupos: 🔴 <b>Críticas (0-5)</b> | 🟡 <b>Neutras (6-7)</b> | 🟢 <b>Promotoras (8-10)</b></div>""", unsafe_allow_html=True)

        df_nt = df[df['Nota'].notna() & df['Data Avaliacao'].notna()].copy()
        if df_nt.empty:
            st.info("Sem avaliações na base.")
        else:
            df_nt['Mes_Aval'] = df_nt['Data Avaliacao'].dt.to_period('M')
            df_nt['Nota Int'] = df_nt['Nota'].astype(int)
            df_nt['Grupo'] = df_nt['Nota Int'].apply(grupo_nota)

            meses_nt = sorted(df_nt['Mes_Aval'].unique(), reverse=True)
            mes_nt = st.selectbox("📅 Mês de referência:", meses_nt, format_func=formatar_mes, key="nt_mes")
            df_nt_mes = df_nt[df_nt['Mes_Aval'] == mes_nt]

            total_nt = len(df_nt_mes)
            criticas = int((df_nt_mes['Grupo'] == 'Críticas (0-5)').sum())
            neutras = int((df_nt_mes['Grupo'] == 'Neutras (6-7)').sum())
            promotoras = int((df_nt_mes['Grupo'] == 'Promotoras (8-10)').sum())
            def pct(qtd): return f"{qtd / total_nt * 100:.0f}% do mês" if total_nt > 0 else "-"

            k_nt1, k_nt2, k_nt3, k_nt4, k_nt5 = st.columns(5)
            k_nt1.markdown(f"""<div class="kpi-container"><div class="kpi-title">Notas Recebidas</div><div class="kpi-value">{total_nt}</div><div style="font-size: 0.7rem; color: #888;">{formatar_mes(mes_nt)}</div></div>""", unsafe_allow_html=True)
            k_nt2.markdown(f"""<div class="kpi-container"><div class="kpi-title">Nota Média</div><div class="kpi-value">{df_nt_mes['Nota'].mean():.2f}</div><div style="font-size: 0.7rem; color: #888;">Meta ≥ 7</div></div>""", unsafe_allow_html=True)
            k_nt3.markdown(f"""<div class="kpi-container"><div class="kpi-title">🔴 Críticas (0-5)</div><div class="kpi-value" style="color: #c62828;">{criticas}</div><div style="font-size: 0.7rem; color: #888;">{pct(criticas)}</div></div>""", unsafe_allow_html=True)
            k_nt4.markdown(f"""<div class="kpi-container"><div class="kpi-title">🟡 Neutras (6-7)</div><div class="kpi-value" style="color: #b57d00;">{neutras}</div><div style="font-size: 0.7rem; color: #888;">{pct(neutras)}</div></div>""", unsafe_allow_html=True)
            k_nt5.markdown(f"""<div class="kpi-container"><div class="kpi-title">🟢 Promotoras (8-10)</div><div class="kpi-value" style="color: #2e7d32;">{promotoras}</div><div style="font-size: 0.7rem; color: #888;">{pct(promotoras)}</div></div>""", unsafe_allow_html=True)

            st.markdown(f"##### 📊 Distribuição das Notas em {formatar_mes(mes_nt)}")
            dist = df_nt_mes['Nota Int'].value_counts().reindex(range(11), fill_value=0).reset_index()
            dist.columns = ['Nota', 'Qtd']
            dist['Grupo'] = dist['Nota'].apply(grupo_nota)
            fig_dist = px.bar(dist, x='Nota', y='Qtd', color='Grupo', text='Qtd',
                              color_discrete_map=COR_GRUPO_NOTA, category_orders={'Grupo': ORDEM_GRUPOS_NOTA})
            fig_dist.update_traces(marker_line_color='white', marker_line_width=2, textposition='outside')
            fig_dist.update_xaxes(dtick=1, title='Nota')
            fig_dist.update_yaxes(title='Quantidade')
            st.plotly_chart(estilizar_grafico(fig_dist), use_container_width=True)

            st.markdown("---")
            st.markdown(f"##### 📈 Evolução Mensal (Últimos 6 Meses até {formatar_mes(mes_nt)})")
            df_h_nt = df_nt[(df_nt['Mes_Aval'] >= mes_nt - 5) & (df_nt['Mes_Aval'] <= mes_nt)].copy()
            df_h_nt = df_h_nt.sort_values('Mes_Aval')
            df_h_nt['Mês'] = df_h_nt['Mes_Aval'].map(formatar_mes)
            ordem_meses_nt = [formatar_mes(p) for p in sorted(df_h_nt['Mes_Aval'].unique())]

            agg_h = df_h_nt.groupby(['Mês', 'Grupo']).size().reset_index(name='Qtd')
            fig_evo = px.bar(agg_h, x='Mês', y='Qtd', color='Grupo', text='Qtd',
                             color_discrete_map=COR_GRUPO_NOTA,
                             category_orders={'Mês': ordem_meses_nt, 'Grupo': ORDEM_GRUPOS_NOTA})
            fig_evo.update_traces(marker_line_color='white', marker_line_width=2, textposition='inside', textangle=0)
            fig_evo.update_layout(barmode='stack', xaxis={'title': None}, yaxis={'title': 'Notas Recebidas'},
                                  uniformtext_minsize=10, uniformtext_mode='hide')
            st.plotly_chart(estilizar_grafico(fig_evo, altura=380), use_container_width=True)

            piv_nt = df_h_nt.pivot_table(index='Mes_Aval', columns='Nota Int', values='ID Reclame Aqui',
                                         aggfunc='count', fill_value=0)
            piv_nt = piv_nt.reindex(columns=range(11), fill_value=0)
            piv_nt['Total'] = piv_nt.sum(axis=1)
            piv_nt['Nota Média'] = df_h_nt.groupby('Mes_Aval')['Nota'].mean()
            piv_nt.index = [formatar_mes(p) for p in piv_nt.index]
            piv_nt.columns = [f'Nota {c}' if isinstance(c, int) else c for c in piv_nt.columns]
            piv_nt = piv_nt.reset_index().rename(columns={'index': 'Mês'})

            st.markdown("##### 📋 Quantidade de Notas por Mês (0 a 10)")
            cols_notas = [c for c in piv_nt.columns if c.startswith('Nota ') and c != 'Nota Média']
            st.dataframe(piv_nt.style
                         .background_gradient(subset=cols_notas, cmap='Blues', axis=None)
                         .format({'Nota Média': '{:.2f}'}),
                         use_container_width=True, hide_index=True)
            st.download_button(label="📥 Baixar Notas por Mês (XLSX)", data=converter_para_excel(piv_nt),
                               file_name='notas_por_mes.xlsx',
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key="dl_nt_piv")

    # --- ABA ANÁLISE POR FRANQUIA (MULTISELECT) ---
    with tab_franquias:
        st.subheader("🏢 Dossiê da Franquia")
        st.markdown("Selecione uma ou mais matrizes (visão unificada) e, se quiser, as franquias de dentro delas. Se deixar vazio, mostrará a **Rede Completa**.")
        
        c_fd1, c_fd2 = st.columns(2)
        d_fran_ini = c_fd1.date_input("Início Período", df['Data Reclamação'].min().date(), key="dfi")
        d_fran_fim = c_fd2.date_input("Fim Período", df['Data Reclamação'].max().date(), key="dff")
        
        mask_fran_time = (df['Data Reclamação'].dt.date >= d_fran_ini) & (df['Data Reclamação'].dt.date <= d_fran_fim)
        df_fran_time = df.loc[mask_fran_time].copy()
        
        if not df_fran_time.empty:
            # 1º nível: Franquia Unificada | 2º nível (opcional): franquias dentro dos grupos escolhidos
            lista_unificadas = sorted(u for u in df_fran_time['Franquia Unificada'].dropna().unique() if u != SEM_FRANQUIA)
            c_sel1, c_sel2 = st.columns(2)
            unificadas_sel = c_sel1.multiselect("📂 Matriz (visão unificada):", lista_unificadas, key="fran_unif")
            base_sub = df_fran_time[df_fran_time['Franquia Unificada'].isin(unificadas_sel)] if unificadas_sel else df_fran_time
            lista_franquias = sorted(f for f in base_sub['Franquia'].dropna().unique() if f != SEM_FRANQUIA)
            franquias_selecionadas = c_sel2.multiselect("🏢 Franquia (opcional, para abrir a matriz):", lista_franquias, key="fran_sub")

            # Lógica de Filtro
            df_target = df_fran_time.copy()  # Vazio = Todas
            if unificadas_sel:
                df_target = df_target[df_target['Franquia Unificada'].isin(unificadas_sel)]
            if franquias_selecionadas:
                df_target = df_target[df_target['Franquia'].isin(franquias_selecionadas)]
            selecao = franquias_selecionadas or unificadas_sel
            if not selecao:
                titulo_painel = "Status: Rede Completa (Todas)"
            elif len(selecao) == 1:
                titulo_painel = f"Status: {selecao[0]}"
            else:
                titulo_painel = f"Status: {len(selecao)} Franquias Selecionadas"
            df_target = df_target.copy()

            if not df_target.empty:
                st.markdown("---")
                renderizar_painel_principal(df_target, titulo_painel)

                if not carregar_matrizes():
                    st.warning(f"Arquivo `{ARQ_MATRIZES}` não encontrado: cada franquia aparece como grupo próprio.")
                st.markdown("##### 📑 Abertura por Franquia")
                base_fr = df_target[df_target['Franquia Unificada'] != SEM_FRANQUIA]
                gb_hier = agregar_franquias(base_fr, ['Franquia Unificada', 'Franquia'])
                if not gb_hier.empty:
                    # regionais identificadas viram uma coluna de texto (ex.: "R02 (5) · R04 (5)")
                    com_rg = base_fr[base_fr['Regional'] != SEM_REGIONAL].groupby(['Franquia Unificada', 'Franquia', 'Regional']).size().reset_index(name='n')
                    com_rg = com_rg.sort_values('n', ascending=False)
                    com_rg['txt'] = com_rg['Regional'] + ' (' + com_rg['n'].astype(str) + ')'
                    regionais = com_rg.groupby(['Franquia Unificada', 'Franquia'])['txt'].agg(' · '.join).reset_index(name='Regionais')
                    gb_hier = gb_hier.merge(regionais, on=['Franquia Unificada', 'Franquia'], how='left')
                    gb_hier['Regionais'] = gb_hier['Regionais'].fillna('')
                    tot_unif = gb_hier.groupby('Franquia Unificada')['Volume'].transform('sum')
                    gb_hier = gb_hier.assign(_t=tot_unif).sort_values(['_t', 'Franquia Unificada', 'Volume'], ascending=[False, True, False]).drop(columns='_t')
                    gb_hier = gb_hier[['Franquia Unificada', 'Franquia', 'Regionais', 'Volume', 'Nota_Media', 'Resolvido_Pct', 'Voltaria_Pct']]
                    st.dataframe(gb_hier.style.format({'Nota_Media': '{:.2f}', 'Resolvido_Pct': '{:.1f}%', 'Voltaria_Pct': '{:.1f}%'}).background_gradient(subset=['Volume'], cmap='Blues'),
                                 use_container_width=True, hide_index=True)
                    st.download_button(label="📥 Baixar Abertura por Franquia (XLSX)", data=converter_para_excel(gb_hier),
                                       file_name='abertura_franquia.xlsx',
                                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key="dl_fran_hier")

                with st.expander("🗺️ Mapa da rede (Matriz › Franquia › Regional)", expanded=False):
                    fig_mapa = mapa_rede(df_target)
                    if fig_mapa is not None:
                        st.plotly_chart(fig_mapa, use_container_width=True)
                    st.caption(f"Clique num bloco para abrir e no topo do mapa para voltar. "
                               f"{int((df_target['Franquia Unificada'] == SEM_FRANQUIA).sum())} caso(s) sem franquia ficam fora do mapa.")
                
                c_g1, c_g2 = st.columns(2)
                with c_g1:
                    st.markdown("##### 🚨 Principais Motivos")
                    if 'Categoria Motivo' in df_target.columns:
                        top_motivos = df_target['Categoria Motivo'].value_counts().reset_index()
                        top_motivos.columns = ['Motivo', 'Qtd']
                        fig_bar = px.bar(top_motivos.head(5), x='Qtd', y='Motivo', orientation='h', height=300)
                        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_bar, use_container_width=True)
                
                with c_g2:
                    st.markdown("##### 📈 Evolução de Volume")
                    df_target['Mes'] = df_target['Data Reclamação'].dt.to_period('M').astype(str)
                    vol_tempo = df_target.groupby('Mes').size().reset_index(name='Volume')
                    fig_line = px.line(vol_tempo, x='Mes', y='Volume', markers=True, height=300)
                    st.plotly_chart(fig_line, use_container_width=True)
                
                st.markdown(f"##### 📋 Lista de Casos")
                st.dataframe(df_target, use_container_width=True)
                
                # --- BOTÃO DOWNLOAD: Casos das Franquias ---
                st.download_button(
                    label="📥 Baixar Casos Selecionados (XLSX)",
                    data=converter_para_excel(df_target),
                    file_name='casos_franquias.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else:
                st.warning("Sem dados para esta seleção.")
        else:
            st.info("Sem dados no período selecionado.")

    # --- ABA ANÁLISES DETALHADAS (COM DRILL-DOWN) ---
    with tab_motivos:
        renderizar_motivos_ra(df)

    with tab_quali:
        st.subheader("🔍 Análise Qualitativa Detalhada")
        c_d1, c_d2 = st.columns(2)
        d_ini = c_d1.date_input("Início Análise", min_date, key="dq_ini")
        d_fim = c_d2.date_input("Fim Análise", max_date, key="dq_fim")
        mask_quali = (df['Data Reclamação'].dt.date >= d_ini) & (df['Data Reclamação'].dt.date <= d_fim)
        df_quali_filtered = df.loc[mask_quali].copy()
        df_q = processar_qualitativo(df_quali_filtered)
        if df_q is not None:
            grupos = df_q.groupby('Categoria Nota')
            cols = st.columns(3)
            faixas = ["Notas Críticas (de 1 à 5)", "Notas Neutras (de 6 à 7)", "Notas Promotoras (de 8 à 10)"]
            bg_colors = ["#ffebee", "#fff8e1", "#e8f5e9"]
            for i, faixa in enumerate(faixas):
                if faixa in grupos.groups:
                    dff = grupos.get_group(faixa)
                    total = len(dff)
                    res_sim = len(dff[dff['Seu problema foi resolvido?'] == 'SIM'])
                    res_nao = len(dff[dff['Seu problema foi resolvido?'] == 'NÃO'])
                    vol_sim = len(dff[dff['Voltaria a fazer negócio?'] == 'SIM'])
                    vol_nao = len(dff[dff['Voltaria a fazer negócio?'] == 'NÃO'])
                    html_card = f"""
<div style="background-color:{bg_colors[i]}; padding:15px; border-radius:10px; border:1px solid #ddd; margin-bottom:10px; color:#333;">
<h4 style="margin:0; text-align:center; color:#000;">{faixa}</h4>
<h2 style="margin:5px 0; text-align:center; color:#000;">{total} Casos</h2>
<hr style="border-top: 1px solid #ccc; margin: 10px 0;">
<div style="margin-bottom:10px; font-size:0.95em;">
<strong>Índice de Solução de Problema:</strong><br><span style="color:#2e7d32; font-weight:bold;">✅ {res_sim} Resolvidos</span><br><span style="color:#c62828; font-weight:bold;">❌ {res_nao} Não Resolvidos</span>
</div>
<div style="font-size:0.95em;">
<strong>Voltaria Fazer Negócio:</strong><br><span style="color:#2e7d32; font-weight:bold;">🤝 {vol_sim} Voltariam</span><br><span style="color:#c62828; font-weight:bold;">🚫 {vol_nao} Não Voltariam</span>
</div>
</div>"""
                    with cols[i]: st.markdown(html_card, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("### 🔬 Detalhamento Cruzado (Drill-down)")
            sel_faixas = st.multiselect("Filtrar Tabela por Faixa de Nota:", faixas, default=faixas)
            df_drill = df_q[df_q['Categoria Nota'].isin(sel_faixas)]
            gb_drill = df_drill.groupby(['Franquias', 'Categoria Motivo', 'Subcategoria Motivo']).agg(
                Qtd_Casos=('ID Reclame Aqui', 'count'),
                Resolvido_Sim=('Seu problema foi resolvido?', lambda x: (x=='SIM').sum()),
                Resolvido_Nao=('Seu problema foi resolvido?', lambda x: (x=='NÃO').sum()),
                Voltaria_Sim=('Voltaria a fazer negócio?', lambda x: (x=='SIM').sum()),
                Voltaria_Nao=('Voltaria a fazer negócio?', lambda x: (x=='NÃO').sum()),
                Nota_Media=('Nota', 'mean')
            ).reset_index().sort_values('Qtd_Casos', ascending=False)
            st.dataframe(gb_drill.style.background_gradient(subset=['Qtd_Casos'], cmap='Blues').format({'Nota_Media': '{:.2f}'}), use_container_width=True)
            
            # --- BOTÃO DE DOWNLOAD: Detalhamento Cruzado ---
            gb_drill_download = gb_drill.copy()
            if 'Nota_Media' in gb_drill_download.columns:
                gb_drill_download['Nota_Media'] = gb_drill_download['Nota_Media'].round(2)
            
            st.download_button(
                label="📥 Baixar Dados (XLSX)",
                data=converter_para_excel(gb_drill_download),
                file_name='detalhamento_cruzado.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        else: st.info("Nenhum caso avaliado.")

    with tab_simulador:
        st.subheader("🎯 Simulador de Metas")
        st.markdown("<div class='explanation-box' style='border-left-color: #faad14;'><b>🛠️ Como usar este simulador?</b><br>1. Os dados base vêm da <b>'⚡ Visão Prévia'</b>.<br>2. Altere os valores de 'Meta' abaixo.<br>3. O sistema calcula o esforço necessário <b>hoje</b> para atingir o objetivo.</div>", unsafe_allow_html=True)
        if 'kpis_previa' in st.session_state and st.session_state['kpis_previa']:
            kp = st.session_state['kpis_previa']
            total_aval = kp['total_avaliadas']
            total_recl = kp['total_reclamacoes'] 
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown("##### Solução (IS)")
                meta_is = st.number_input("Meta IS (%)", 90.0, 100.0, 90.0, step=0.1)
                if kp['IS'] < meta_is:
                    nec = math.ceil(((meta_is - kp['IS']) * total_aval) / (100 - meta_is))
                    st.warning(f"Faltam **{nec}** 'Sim'")
                else: st.success("Meta Atingida!")
            with c2:
                st.markdown("##### Voltaria (IN)")
                meta_in = st.number_input("Meta IN (%)", 70.0, 100.0, 70.0, step=0.1)
                if kp['IN'] < meta_in:
                    nec = math.ceil(((meta_in - kp['IN']) * total_aval) / (100 - meta_in))
                    st.warning(f"Faltam **{nec}** 'Sim'")
                else: st.success("Meta Atingida!")
            with c3:
                st.markdown("##### Nota (MA)")
                meta_ma = st.number_input("Meta MA", 0.0, 10.0, 7.0, step=0.1)
                if kp['MA'] < meta_ma:
                    soma_atual = kp['MA'] * total_aval
                    if (10 - meta_ma) > 0:
                        nec = math.ceil((meta_ma * total_aval - soma_atual) / (10 - meta_ma))
                        st.warning(f"Faltam **{nec}** notas 10")
                    else: st.error("Impossível")
                else: st.success("Meta Atingida!")
            with c4:
                st.markdown("##### Resposta (IR)")
                meta_ir = st.number_input("Meta IR (%)", 90.0, 100.0, 90.0, step=0.1)
                if kp['IR'] < meta_ir:
                    meta_dec = meta_ir / 100
                    if (1 - meta_dec) > 0:
                        nec = math.ceil((meta_dec * total_recl - kp['respondidas']) / (1 - meta_dec))
                        st.warning(f"Responder +**{nec}** casos")
                    else: st.error("Check Math")
                else: st.success("Meta Atingida!")
        else: st.info("⚠️ Carregue a aba '⚡ Visão Prévia' primeiro.")

    # --- ABA ANÁLISES AVANÇADAS (RESTRITA: COMPARADOR + IA) ---
    with tab_avancada:
        st.subheader("🔐 Análises Avançadas (Restrito)")
        
        senha = st.text_input("Digite a senha para acessar:", type="password")
        
        if senha == "1010":
            st.success("Acesso Liberado!")
            st.markdown("---")
            
            # SUB-ABAS INTERNAS
            sub_comparador, sub_ia = st.tabs(["⚖️ Comparador de Períodos", "🤖 Assistente IA"])
            
            # --- SUB-ABA COMPARADOR ---
            with sub_comparador:
                st.markdown("Compare o desempenho entre dois períodos distintos para identificar evoluções.")
                min_d = df['Data Reclamação'].min().date()
                max_d = df['Data Reclamação'].max().date()
                
                c_comp1, c_comp2 = st.columns(2)
                with c_comp1:
                    st.markdown("**Período 1 (Referência)**")
                    d1_ini = st.date_input("Início P1", min_d, min_value=min_d, max_value=max_d, key="d1i")
                    d1_fim = st.date_input("Fim P1", max_d - timedelta(days=30), min_value=min_d, max_value=max_d, key="d1f")
                with c_comp2:
                    st.markdown("**Período 2 (Atual)**")
                    d2_ini = st.date_input("Início P2", max_d - timedelta(days=29), min_value=min_d, max_value=max_d, key="d2i")
                    d2_fim = st.date_input("Fim P2", max_d, min_value=min_d, max_value=max_d, key="d2f")
                
                st.markdown("---")
                
                mask1 = (df['Data Reclamação'].dt.date >= d1_ini) & (df['Data Reclamação'].dt.date <= d1_fim)
                mask2 = (df['Data Reclamação'].dt.date >= d2_ini) & (df['Data Reclamação'].dt.date <= d2_fim)
                df1, df2 = df.loc[mask1], df.loc[mask2]
                
                if not df1.empty and not df2.empty:
                    k1, k2 = calcular_indicadores(df1), calcular_indicadores(df2)
                    
                    def metric_comp(label, val1, val2, suffix="", inverse=False):
                        delta = val2 - val1
                        col_delta = "inverse" if inverse else "normal"
                        st.metric(label=label, value=f"{val2:.1f}{suffix}", delta=f"{delta:.1f}{suffix}", delta_color=col_delta, help=f"Período 1: {val1:.1f}{suffix}")

                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    with c1: metric_comp("Score AR", k1['AR'], k2['AR'])
                    with c2: metric_comp("Nota MA", k1['MA'], k2['MA'])
                    with c3: metric_comp("Resposta IR", k1['IR'], k2['IR'], "%")
                    with c4: metric_comp("Solução IS", k1['IS'], k2['IS'], "%")
                    with c5: metric_comp("Voltaria IN", k1['IN'], k2['IN'], "%")
                    with c6: metric_comp("Tempo Médio", k1['Tempo_Medio'], k2['Tempo_Medio'], "d", inverse=True)
                    st.caption(f"*Delta mostra a diferença do Período 2 em relação ao Período 1.")
                else: st.warning("Selecione períodos com dados para comparação.")

            # --- SUB-ABA ASSISTENTE IA ---
            with sub_ia:
                st.markdown(
                    """
                    <div class='explanation-box'>
                        <b>💡 Como usar?</b><br>
                        1. Selecione o período abaixo.<br>
                        2. Escolha um cenário (Estratégia, Plano de Ação ou Franquias).<br>
                        3. Copie o texto gerado e cole no ChatGPT/Claude para análise.
                    </div>
                    """, unsafe_allow_html=True
                )
                
                c_ia1, c_ia2 = st.columns(2)
                d_ia_ini = c_ia1.date_input("Início Análise IA", df['Data Reclamação'].min().date())
                d_ia_fim = c_ia2.date_input("Fim Análise IA", df['Data Reclamação'].max().date())
                
                mask_ia = (df['Data Reclamação'].dt.date >= d_ia_ini) & (df['Data Reclamação'].dt.date <= d_ia_fim)
                df_ia = df.loc[mask_ia].copy()
                
                if not df_ia.empty:
                    kpis_ia = calcular_indicadores(df_ia)
                    
                    top_motivos_ruins = pd.DataFrame()
                    if 'Subcategoria Motivo' in df_ia.columns:
                        agg_mot = df_ia.groupby('Subcategoria Motivo').agg(Vol=('ID Reclame Aqui','count'), Nota=('Nota','mean')).reset_index().sort_values('Nota', ascending=True)
                        top_motivos_ruins = agg_mot[agg_mot['Vol']>0].head(5)
                    
                    piores_franquias = pd.DataFrame()
                    if 'Franquias' in df_ia.columns:
                        agg_fran = df_ia.groupby('Franquias').agg(Vol=('ID Reclame Aqui','count'), Nota=('Nota','mean')).reset_index().sort_values('Nota', ascending=True)
                        piores_franquias = agg_fran[agg_fran['Vol']>0].head(5)

                    cenario = st.selectbox("Escolha o cenário:", ["🧠 Diagnóstico Estratégico (Diretoria)", "🛠️ Plano de Ação (Ofensores)", "store Consultoria de Franquias"])
                    
                    prompt_text = ""
                    if "Diagnóstico Estratégico" in cenario:
                        prompt_text = f"""Atue como um Consultor Sênior de Customer Experience (CX). Analise os dados da Culligan ({d_ia_ini} a {d_ia_fim}):\n- Vol: {kpis_ia['total_reclamacoes']}\n- AR: {kpis_ia['AR']:.2f}\n- IR: {kpis_ia['IR']:.1f}%\n- MA: {kpis_ia['MA']:.2f}\n- IS: {kpis_ia['IS']:.1f}%\n- IN: {kpis_ia['IN']:.1f}%\nTAREFA:\n1. Resumo Executivo dos riscos.\n2. Diagnóstico da relação Nota x Solução.\n3. 3 ações estratégicas para subir o Score."""
                    elif "Plano de Ação" in cenario:
                        prompt_text = f"""Atue como Gerente de Operações. Maiores ofensores (menor nota):\n{top_motivos_ruins.to_string(index=False)}\nTAREFA:\nPara cada motivo:\n1. Hipótese de causa raiz.\n2. Ação corretiva imediata.\n3. Ação estrutural."""
                    elif "Consultoria de Franquias" in cenario:
                        prompt_text = f"""Atue como Gerente de Rede. Franquias com pior nota:\n{piores_franquias.to_string(index=False)}\nTAREFA:\n1. Roteiro de feedback para os gestores.\n2. Perguntas diagnósticas.\n3. Plano de recuperação de 30 dias."""

                    st.code(prompt_text, language="text")
                else: st.warning("Sem dados no período.")

        elif senha != "":
            st.error("Senha incorreta!")
        else:
            st.info("Por favor, insira a senha para visualizar os geradores de estratégia.")

    with tab_dados:
        st.subheader("📂 Base de Dados")
        with st.expander("🧠 Memória de tags do HugMe (franquia, cancelamento e marca)"):
            mem_atual = carregar_memoria_tags()
            n_mem = int((df['Franquia pela memória'] == 'Sim').sum())
            n_sem = int((df['Franquia Unificada'] == SEM_FRANQUIA).sum())
            st.markdown("Guarda o último valor conhecido de cada ticket, para o dash não perder a informação quando a tag some do HugMe. "
                        f"Na base atual: **{n_mem}** franquias vieram da memória · **{len(df) - n_mem - n_sem}** vieram da própria Base Eco "
                        f"ou das sugestões aprovadas · **{n_sem}** sem franquia. Tickets na memória: **{len(mem_atual)}**.")
            st.markdown("**Para manter a memória em dia:** depois de trocar a Base Eco, baixe o arquivo abaixo, salve por cima de "
                        f"`{ARQ_MEMORIA}` na pasta do dash e rode o Atualizar RA.")
            mem_nova = memoria_atualizada(df)
            st.download_button(label=f"📥 Baixar memória atualizada ({len(mem_nova)} tickets)", data=converter_para_excel(mem_nova),
                               file_name=ARQ_MEMORIA, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key="dl_memoria")
        search_id = st.text_input("🔍 Pesquisar por ID Origem ou ID Reclame Aqui:", placeholder="Digite o ID e pressione Enter")
        df_display = df.copy()
        if search_id:
            m1 = df_display['Id Origem'].astype(str).str.contains(search_id, case=False, na=False)
            m2 = df_display['ID Reclame Aqui'].astype(str).str.contains(search_id, case=False, na=False)
            df_display = df_display[m1 | m2]
        
        st.dataframe(df_display, use_container_width=True)
        
        # --- BOTÃO DOWNLOAD: Base de Dados ---
        st.download_button(
            label="📥 Baixar Base Atual (XLSX)",
            data=converter_para_excel(df_display),
            file_name='base_completa_filtrada.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

if __name__ == "__main__":
    main()
