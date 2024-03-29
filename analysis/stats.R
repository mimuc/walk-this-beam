# Copyright © 2022 LMU Munich Media Informatics Group. All rights reserved.
# Written by Changkun Ou <https://changkun.de>.
#
# Use of this source code is governed by a GNU GPLv3 license that
# can be found in the LICENSE file.

library(ARTool)
library(dplyr)
library(report)
library(apa)
library(ez)         # for ezANOVA
library(effectsize) # for eta_squared and omega_squared
library(car)        # for leveneTest

round_correct <- function(x, digits, chars = TRUE) {
    x <- round(x, digits)
    if(grepl(x = x, pattern = "\\.")) {
        y <- as.character(x)
        pos <- grep(unlist(strsplit(x = y, split = "")), pattern = "\\.", value = FALSE)
        if(chars) {
            return(substr(x = x, start = 1, stop = pos + digits))
        }
        return(
            as.numeric(substr(x = x, start = 1, stop = pos + digits))
        )
    } else {
        return(
            format(round(x, 2), nsmall = 2)
        )
    }
}

twoway_anova_test <- function(df, feature) {
    sig <- shapiro.test(df[[feature]])
    if (sig$p < 0.05) {
        print("not normally distributed:")
        print(sig)
        f <- as.formula(paste(feature, "~ method * tide + (1 | user_id)"))
        print(f)
        m <- art(f, data = df)
        a <- anova(m)
        print(summary(a))
        print(a, verbose = TRUE)
        print(eta_squared(m, partial = TRUE))
        o <- omega_squared(m)
        print(o)
        print(art.con(m, "method:tide", adjust = "holm") %>%
        summary() %>%
        mutate(sig. = symnum(p.value, corr = FALSE, na = FALSE,
                            cutpoints = c(0, .001, .01, .05, .10, 1),
                            symbols = c("***", "**", "*", ".", " "))))

        # hacking table generalization
        rows <- c(1, 2, 3)
        cols <- c(3, 4, 2, 5)
        line <- c()
        for (r in rows) {
            for (c in cols) {
                if (c == 3 || c == 4) {
                    line <- append(line, as.integer(round_correct(a[r, c], 0)))
                } else {
                    v <- round_correct(a[r, c], 3)
                    if (v < .001) {
                        v <- "\\textbf{< .001}"
                    }
                    if (v < .05) {
                        v <- paste("\\textbf{", v, "}", sep = "")
                    }
                    line <- append(line, v)
                }
            }
            line <- append(line, round_correct(o[r, 2], 3))
        }
        cat(line, sep = " & ")
    } else {
        print("normally distributed:")
        print(sig)
        model <- eval(parse(text = paste0("ezANOVA(data=df, dv=", feature,
            ", within = .(method, tide), wid = user_id, detailed = TRUE)")))
        print(summary(model))
        anova_apa(model)

        # hacking table generalization
        a <- model[["ANOVA"]]
        rows <- c(2, 3, 4)
        cols <- c(2, 3, 6, 7, 9)
        line <- c()
        for (r in rows) {
            for (c in cols) {
                if (c == 2 || c == 3) {
                    line <- append(line, as.integer(round_correct(a[r, c], 0)))
                } else {
                    v <- round_correct(a[r, c], 3)
                    if (v < .001) {
                        v <- "\\textbf{< .001}"
                    }
                    if (c == 7 && v < .05) {
                        v <- paste("\\textbf{", v, "}", sep = "")
                    }
                    line <- append(line, v)
                }
            }
        }
        cat(line, sep = " & ")
    }
}

independent_test <- function(df, factor, level1, level2, response) {
    df1 <- df %>% dplyr::filter({{factor}} == level1) %>% pull({{response}})
    df2 <- df %>% dplyr::filter({{factor}} == level2) %>% pull({{response}})
    # normality test
    s1 <- shapiro.test(df1)
    s2 <- shapiro.test(df2)
    nd <- s1$p >= 0.05 && s2$p >= 0.05
    # for equal variance test: Levenes test
    f <- as.formula(paste(response, "~", factor))
    l <- leveneTest(f, data = df, center = "mean")
    eq_var <- l$`Pr(>F)`[[1]] >= 0.05
    if (nd) {
        # parametric: t test
        m <- t.test(df1, df2, var.equal = eq_var, na.rm = TRUE)
        print(m)
        report(m)
    } else {
        # non-parametric: mann-whitney u test
        m <- wilcox.test(df1, df2)
        print(m)
        report(m)
    }
}
