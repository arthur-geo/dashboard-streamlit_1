# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 12:45:46 2024

@author: arthu
"""

#%%

from PyPDF2 import PdfMerger

# Cria o objeto merger
merger = PdfMerger()

# Lista de arquivos PDF que deseja juntar
arquivos = ["Recibo_14_31_outubro.pdf", "AUXILIO TRANSPORTE)14_31_outubro.pdf", "Frequencia_15_31_de_outubro.pdf"]  

# Adiciona cada arquivo na lista para o merger
for arquivo in arquivos:
    merger.append(arquivo)

# Salva o PDF final com o nome desejado
merger.write("arthur_bolsa_auxilio_frequencia_14a31_outubro.pdf")
merger.close()

print("PDFs combinados com sucesso!")
