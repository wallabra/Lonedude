# Lonedude: A simple IRC MCMC engine
* IRC stands for Internet Relay Chat: it will respond by command or highlight.
* MCMC stands for Markov Chain Monte Carlo - it will generate random strings based on previous input and fed parse data.

## How to Use

    **git clone https://www.github.com/Gustavo6046/Lonedude**
    **cd Lonedude**
    **cp config.example.json config.json**
    **nano config.json** # edit to your likings
    **pypy3 main.py**

If you want to parse text files inside the `parsedata` directory, such that:

    **ls parsedata** 
    stuff.txt

Then do:

    **pypy3 main.py stuff.txt**
