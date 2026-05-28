library(tidyverse)
library(naniar)
library(googlesheets4)
library(phytools)
library(RColorBrewer)

braztad <- read_sheet("https://docs.google.com/spreadsheets/d/1Zn_8-CVmmPCmueLcpnT36TrFS3ZI9lBsWKcNzyoZreE/edit#gid=1996126092")
braztad
unique(braztad$Family)

phyloBraz <- read.tree(text="((((((Aromobatidae,Dendrobatidae),((Bufonidae,Odontophrynidae),(Leptodactylidae,(Allophrynidae,Centrolenidae)))),((Ceratophryidae,Hemiphractidae),Hylidae)),(Alsodidae,(Hylodidae,Cycloramphidae))),(Ranidae,Microhylidae)),Pipidae);")

plotTree(phyloBraz)

commiss <- braztad %>%
        mutate(external=na_if(`External Morphology`, "Not_described"), internal=na_if(`Internal Oral Features`, "Not_described"), cond=na_if(Chondrocranium, "Not_described"))

# Supondo que seu dataframe se chama "seu_dataframe"
resultado <- commiss %>%
       #select(external) %>%
       group_by(Family) %>%
       summarise(
              Prop_com = prop_complete(external),
              Prop_Faltantes_ext = prop_miss(external)      
       ) %>%
       ungroup() %>%
       mutate(Family = as.factor(Family))

print(resultado)

braz_tree <- compute.brlen(phyloBraz, power = 1)

figure <- column_to_rownames(resultado, var = "Family")

cols<-c("7FC97F","BEAED4")

plotTree.barplot(braz_tree,figure, 
                 args.barplot = list(legend.text=TRUE))

resultado_int <- commiss %>%
       #select(external) %>%
       group_by(Family) %>%
       summarise(
              Prop_com = prop_complete(internal),
              Prop_Faltantes_ext = prop_miss(internal)      
       ) %>%
       ungroup() %>%
       mutate(Family = as.factor(Family))

figure2 <- column_to_rownames(resultado_int, var = "Family")

plotTree.barplot(braz_tree,figure2, 
                 args.barplot = list(legend.text=TRUE))

resultado_cond <- commiss %>%
       #select(external) %>%
       group_by(Family) %>%
       summarise(
              Prop_com = prop_complete(cond),
              Prop_Faltantes_ext = prop_miss(cond)      
       ) %>%
       ungroup() %>%
       mutate(Family = as.factor(Family))

figure3 <- column_to_rownames(resultado_cond, var = "Family")

plotTree.barplot(braz_tree,figure3, 
                 args.barplot = list(legend.text=TRUE))
