import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
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

# --- FUNÇÕES ---

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
        meses = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho',
                 7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
        nome_mes = f"{meses[periodo.month]} {periodo.year}"
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

@st.cache_data
def carregar_dados():
    file_path = 'BaseEco.xlsx'
    if not os.path.exists(file_path): return None
    df = pd.read_excel(file_path)
    df['Data Reclamação'] = pd.to_datetime(df['Data Reclamação'])
    if 'Data de Resposta' in df.columns:
        df['Data de Resposta'] = pd.to_datetime(df['Data de Resposta'], errors='coerce')
    cols_str = ['Status RA', 'Seu problema foi resolvido?', 'Voltaria a fazer negócio?', 'Motivos Ecohouse', 'Franquias', 'Origem', 'Marca']
    for col in cols_str:
        if col in df.columns: df[col] = df[col].astype(str).str.strip().str.upper()
        else:
            if col in ['Motivos Ecohouse', 'Franquias']: df[col] = "NÃO INFORMADO"
    df = df.replace('NAN', pd.NA)
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

    tab_oficial, tab_previa, tab_mensal, tab_franquias, tab_analises, tab_quali, tab_simulador, tab_avancada, tab_dados = st.tabs([
        "🔒 Visão Oficial", "⚡ Visão Prévia", "📅 Evolução Mensal", "🏢 Análise por Franquia",
        "📊 Análises Detalhadas", "🔍 Análise Qualitativa", 
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

    # --- ABA ANÁLISE POR FRANQUIA (MULTISELECT) ---
    with tab_franquias:
        st.subheader("🏢 Dossiê da Franquia")
        st.markdown("Selecione uma ou mais franquias. Se deixar vazio, mostrará a **Rede Completa**.")
        
        c_fd1, c_fd2 = st.columns(2)
        d_fran_ini = c_fd1.date_input("Início Período", df['Data Reclamação'].min().date(), key="dfi")
        d_fran_fim = c_fd2.date_input("Fim Período", df['Data Reclamação'].max().date(), key="dff")
        
        mask_fran_time = (df['Data Reclamação'].dt.date >= d_fran_ini) & (df['Data Reclamação'].dt.date <= d_fran_fim)
        df_fran_time = df.loc[mask_fran_time].copy()
        
        if not df_fran_time.empty:
            lista_franquias = df_fran_time['Franquias'].dropna().astype(str).unique().tolist()
            if "NÃO INFORMADO" in lista_franquias: lista_franquias.remove("NÃO INFORMADO")
            lista_franquias.sort()
            
            # MULTISELECT
            franquias_selecionadas = st.multiselect("📂 Selecione as Franquias:", lista_franquias)
            
            # Lógica de Filtro
            if not franquias_selecionadas:
                df_target = df_fran_time.copy() # Vazio = Todas
                titulo_painel = "Status: Rede Completa (Todas)"
            else:
                df_target = df_fran_time[df_fran_time['Franquias'].isin(franquias_selecionadas)].copy()
                if len(franquias_selecionadas) == 1:
                    titulo_painel = f"Status: {franquias_selecionadas[0]}"
                else:
                    titulo_painel = f"Status: {len(franquias_selecionadas)} Franquias Selecionadas"
            
            if not df_target.empty:
                st.markdown("---")
                renderizar_painel_principal(df_target, titulo_painel)
                
                c_g1, c_g2 = st.columns(2)
                with c_g1:
                    st.markdown("##### 🚨 Principais Motivos")
                    if 'Motivos Ecohouse' in df_target.columns:
                        top_motivos = df_target['Motivos Ecohouse'].value_counts().reset_index()
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
    with tab_analises:
        st.subheader("🧩 Análise Detalhada: Motivos & Franquias")
        
        min_date = df['Data Reclamação'].min().date()
        max_date = df['Data Reclamação'].max().date()
        c_m1, c_m2 = st.columns(2)
        dm_ini = c_m1.date_input("Início (Análises)", min_date, key="dm_ini")
        dm_fim = c_m2.date_input("Fim (Análises)", max_date, key="dm_fim")
        
        mask_mot = (df['Data Reclamação'].dt.date >= dm_ini) & (df['Data Reclamação'].dt.date <= dm_fim)
        df_analise = df.loc[mask_mot].copy()

        if 'Motivos Ecohouse' in df_analise.columns and 'Franquias' in df_analise.columns:
            st.markdown("---")
            st.markdown("### 1. Visão por Motivos (Drill-down)")
            
            lista_motivos_raw = df_analise['Motivos Ecohouse'].dropna().astype(str).unique().tolist()
            if "NÃO INFORMADO" in lista_motivos_raw: lista_motivos_raw.remove("NÃO INFORMADO")
            motivos_list = ["Todos (Visão Geral)"] + sorted(lista_motivos_raw)
            
            filtro_motivo = st.selectbox("🎯 Selecione um motivo para ver quais Franquias são responsáveis:", options=motivos_list)
            
            c1, c2 = st.columns([1.3, 1])
            with c1:
                if filtro_motivo == "Todos (Visão Geral)":
                    gb_motivos = df_analise.groupby('Motivos Ecohouse').agg(Volume=('ID Reclame Aqui', 'count'), Nota_Media=('Nota', 'mean'), Resolvido_Pct=('Seu problema foi resolvido?', lambda x: (x=='SIM').mean() * 100), Voltaria_Pct=('Voltaria a fazer negócio?', lambda x: (x=='SIM').mean() * 100)).reset_index().sort_values('Volume', ascending=False)
                    st.markdown("##### 📋 Ranking de Motivos (Geral)")
                    st.dataframe(gb_motivos.style.format({'Nota_Media': '{:.2f}', 'Resolvido_Pct': '{:.1f}%', 'Voltaria_Pct': '{:.1f}%'}).background_gradient(subset=['Volume'], cmap='Blues'), use_container_width=True, height=400)
                    dados_grafico = gb_motivos.head(10)
                    coluna_grafico = 'Motivos Ecohouse'
                    titulo_grafico = "Top 10 Motivos (Volume)"
                    
                    # --- BOTÃO DOWNLOAD: Motivos Geral ---
                    st.download_button(
                        label="📥 Baixar Ranking de Motivos (XLSX)",
                        data=converter_para_excel(gb_motivos),
                        file_name='ranking_motivos.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                else:
                    df_filtered = df_analise[df_analise['Motivos Ecohouse'] == filtro_motivo]
                    gb_drilldown = df_filtered.groupby('Franquias').agg(Volume=('ID Reclame Aqui', 'count'), Nota_Media=('Nota', 'mean'), Resolvido_Pct=('Seu problema foi resolvido?', lambda x: (x=='SIM').mean() * 100), Voltaria_Pct=('Voltaria a fazer negócio?', lambda x: (x=='SIM').mean() * 100)).reset_index().sort_values('Volume', ascending=False)
                    st.markdown(f"##### 🏢 Franquias com reclamações de: **{filtro_motivo}**")
                    st.dataframe(gb_drilldown.style.format({'Nota_Media': '{:.2f}', 'Resolvido_Pct': '{:.1f}%', 'Voltaria_Pct': '{:.1f}%'}).background_gradient(subset=['Volume'], cmap='Reds'), use_container_width=True, height=400)
                    dados_grafico = gb_drilldown.head(10)
                    coluna_grafico = 'Franquias'
                    titulo_grafico = f"Top Franquias em: {filtro_motivo}"
                    
                    # --- BOTÃO DOWNLOAD: Drill-down Motivo ---
                    st.download_button(
                        label="📥 Baixar Franquias por Motivo (XLSX)",
                        data=converter_para_excel(gb_drilldown),
                        file_name=f'motivo_{filtro_motivo}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )

            with c2:
                if not dados_grafico.empty:
                    fig = px.pie(dados_grafico, values='Volume', names=coluna_grafico, hole=0.4, title=titulo_grafico, color_discrete_sequence=px.colors.sequential.Blues_r)
                    fig.update_traces(textposition='outside', textinfo='percent+label')
                    fig.update_layout(showlegend=False, margin=dict(t=40, b=40, l=40, r=40))
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Sem dados para exibir gráfico.")

            st.markdown("---") 
            st.markdown("### 2. Ranking Geral de Franquias (Volume Total)")
            gb_fran_geral = df_analise.groupby('Franquias').agg(Volume=('ID Reclame Aqui', 'count'), Nota_Media=('Nota', 'mean'), Resolvido_Pct=('Seu problema foi resolvido?', lambda x: (x=='SIM').mean() * 100), Voltaria_Pct=('Voltaria a fazer negócio?', lambda x: (x=='SIM').mean() * 100)).reset_index().sort_values('Volume', ascending=False)
            st.dataframe(gb_fran_geral.style.format({'Nota_Media': '{:.2f}', 'Resolvido_Pct': '{:.1f}%', 'Voltaria_Pct': '{:.1f}%'}).background_gradient(subset=['Volume'], cmap='Blues'), use_container_width=True)
            
            # --- BOTÃO DOWNLOAD: Ranking Geral de Franquias ---
            st.download_button(
                label="📥 Baixar Ranking Geral de Franquias (XLSX)",
                data=converter_para_excel(gb_fran_geral),
                file_name='ranking_geral_franquias.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

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
            gb_drill = df_drill.groupby(['Franquias', 'Motivos Ecohouse']).agg(
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
                    if 'Motivos Ecohouse' in df_ia.columns:
                        agg_mot = df_ia.groupby('Motivos Ecohouse').agg(Vol=('ID Reclame Aqui','count'), Nota=('Nota','mean')).reset_index().sort_values('Nota', ascending=True)
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
