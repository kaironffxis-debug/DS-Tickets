# Guia de Deploy - Bot Discord

## ✅ Estrutura Local (Verificado)
- ✓ discord.py 2.7.1 instalado localmente
- ✓ Bot funciona com `@bot.tree.command()`

## 🚀 Deploy em Ambiente Cloud

### **Heroku**
```bash
heroku login
heroku create seu-app-name
git push heroku main
```

### **Railway.app** (Recomendado - Grátis)
1. Conecte seu GitHub
2. Selecione o repositório
3. Railway detecta automaticamente `requirements.txt`

### **PythonAnywhere**
1. Upload dos arquivos via Web interface
2. Configure o arquivo .env no servidor
3. Execute: `pip install -r requirements.txt`

### **Replit**
1. Upload dos arquivos
2. Replit detecta `requirements.txt` automaticamente
3. Clique em "Run"

## ⚠️ Checklist Antes de Deploy

- [ ] `.env` com TOKEN e PIX_KEY configurado
- [ ] Arquivo `requirements.txt` presente
- [ ] Python 3.11+ no servidor
- [ ] Arquivo `Procfile` presente (Heroku)

## 🔧 Se ainda receber erro `'Bot' object has no attribute 'tree'`

Seu ambiente cloud pode ter discord.py versão 1.x. Force a atualização:

```bash
pip install --force-reinstall --upgrade discord.py>=2.0.0
```

Ou verifique a versão instalada:
```bash
python -c "import discord; print(discord.__version__)"
```

Deve mostrar version 2.0.0 ou superior.
