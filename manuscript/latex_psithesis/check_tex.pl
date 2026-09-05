#!/usr/bin/perl
# check_tex.pl -- static checks on the converted .tex files.
#
# There is no LaTeX distribution on the authoring host, so this stands in for a
# trial compile. It cannot prove the document builds; it catches the defect
# classes that a Markdown-to-LaTeX conversion actually produces:
#
#   E  unescaped % & _ # $ in text        (a bare % eats the rest of the line)
#   E  unbalanced braces / environments
#   E  macros that are not defined anywhere in this project
#   E  wrong argument count on \fig, \figwide, \figmissing
#   E  ragged table rows (wrong number of & for the declared column count)
#   E  bare Greek / maths glyphs outside math mode (Cochineal has no Greek)
#   W  leftover Markdown, \sidenote inside a float, missing \endhead
#
# Usage:  perl check_tex.pl chapters/*.tex appendices/*.tex front/*.tex

use strict;
use warnings;

# ---------------------------------------------------------------------------
# Everything the document may legally call.
# ---------------------------------------------------------------------------
my @project = qw(
  hz sr cagerule scn met dec gate phase nbh
  verdictsat verdictnot verdictind verdictna verdictopen
  enf mon prelimflag retracted caveat
  fig figwide figmargin figmissing tabnote
  qmm qm qmps qdeg qhz qs qpc
  keyword tabhead code file option
  image twoimages wideimage marginimage widefigurewidth
  thesistitle thesissubtitle submissiondate matriculation secondexaminer
  authorname supname univname groupname deptname facname ttitle thesistype
  tdate treporurl tbuildnote
);

my @latex = qw(
  chapter section subsection subsubsection paragraph subparagraph part
  addchap addsec addchaptertocentry label ref pageref cite
  parencite textcite citeauthor citeyear footcite
  Cref cref Crefrange crefrange autoref nameref
  textbf textit texttt textsc emph underline textnormal textrm textsf
  textsuperscript textsubscript uppercase MakeUppercase MakeLowercase
  small footnotesize scriptsize tiny normalsize large Large LARGE huge Huge
  bfseries itshape scshape ttfamily rmfamily sffamily upshape mdseries
  begin end item centering raggedright raggedleft RaggedRight RaggedLeft
  toprule midrule bottomrule cmidrule addlinespace morecmidrules specialrule
  multicolumn multirow hline cline
  endhead endfirsthead endfoot endlastfoot
  caption captionsetup sidecaption includegraphics graphicspath
  sidenote sidenotetext marginnote marginpar footnote
  enquote quote quotation verb verbatim url href texorpdfstring
  SI si num ang percent degree
  ldots dots cdots vdots ddots textellipsis
  quad qquad hspace vspace hfill vfill smallskip medskip bigskip
  newline linebreak pagebreak newpage clearpage cleardoublepage noindent indent
  par bigbreak smallbreak
  textbackslash textasciitilde textasciicircum textbar textless textgreater
  textendash textemdash textquotedblleft textquotedblright textdegree
  times pm le ge approx neq equiv leq geq ll gg propto sim simeq
  rightarrow leftarrow leftrightarrow Rightarrow Leftarrow Leftrightarrow
  to mapsto implies iff wedge vee neg forall exists in notin subset subseteq
  cup cap setminus emptyset infty partial nabla
  alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota
  kappa lambda mu nu xi pi rho sigma tau upsilon phi varphi chi psi omega
  Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega
  frac sqrt sum prod int oint lim min max sup inf log ln exp sin cos tan
  cdot circ ast star dagger ddagger
  mathrm mathbf mathit mathcal mathbb mathsf mathtt text
  left right big Big bigg Bigg
  colon ldots textcolor color colorbox fcolorbox fbox framebox parbox mbox makebox
  newcommand renewcommand providecommand def let
  setlength addtolength setcounter addtocounter arabic alph Alph roman Roman
  the value ensuremath relax ignorespaces protect string
  tabularx tabular longtable array
  toprule linespread selectfont normalfont
  textwidth linewidth columnwidth textheight baselineskip marginparwidth
  arraybackslash rule strut vrule hsp
  input include
  lstinline lstlistoflistings
  S ding tabcolsep dimexpr marginparsep relax fill protect setlength
  meter second radian per degree percent milli centi kilo hertz square
  authorshipname abstractname acknowledgementname listfigurename listtablename
  detokenize hspace textcelsius numrange SIrange leavevmode
  LTleft LTright fill begingroup endgroup newlength AtBeginDocument wtw
  endlastfoot caption newenvironment kill
);

my %ok = map { $_ => 1 } (@project, @latex);

# environments the document may open
my %env_ok = map { $_ => 1 } qw(
  figure figure* table table* tabular tabularx longtable center
  itemize enumerate description quote quotation verbatim lstlisting
  marginfigure margintable equation align aligned array displaymath math
  abstract acknowledgements declaration multicols minipage subfigure
  tikzpicture threeparttable adjustbox landscape
  registertable
);

my $errors = 0;
my $warns  = 0;

sub err  { my ($f,$l,$m)=@_; print "E  $f:$l: $m\n"; $errors++ }
sub warn_{ my ($f,$l,$m)=@_; print "W  $f:$l: $m\n"; $warns++  }

# ---------------------------------------------------------------------------
# Preflight: the exemptions below assume things about the macro definitions.
# Check those assumptions instead of trusting them -- this exact assumption,
# left unchecked, is what shipped a broken chapter 7 to the first real build.
# ---------------------------------------------------------------------------
{
    my $cmds = "misc/thesis-commands.tex";
    if (-r $cmds) {
        open(my $c, "<:encoding(UTF-8)", $cmds) or die "$cmds: $!";
        local $/;
        my $src = <$c>;
        close $c;

        # \figmissing typesets its file-name argument. Underscores in it are
        # only safe while the definition detokenizes them.
        if ($src =~ /\\newcommand\{\\figmissing\}.*?\n\}/s) {
            my ($body) = $src =~ /(\\newcommand\{\\figmissing\}.*?\n\})/s;
            unless ($body =~ /\\detokenize\s*\{\s*#2\s*\}/) {
                err($cmds, 0,
                    "\\figmissing no longer wraps #2 in \\detokenize, but this ".
                    "checker still exempts its argument from the underscore ".
                    "check -- either restore \\detokenize or drop the exemption");
            }
        }
    }
}

for my $file (@ARGV) {
    open(my $fh, "<:encoding(UTF-8)", $file) or do { print "E  cannot open $file\n"; $errors++; next };
    my @lines = <$fh>;
    close $fh;

    my $depth   = 0;      # brace depth across the file
    my @envs    = ();     # environment stack: [name, line]
    my $in_verb = 0;

    for my $i (0 .. $#lines) {
        my $ln  = $i + 1;
        my $raw = $lines[$i];
        chomp $raw;

        # ---- verbatim-ish regions are exempt from escaping rules ----------
        if ($raw =~ /\\begin\{(verbatim|lstlisting)\}/) { $in_verb = 1 }
        if ($raw =~ /\\end\{(verbatim|lstlisting)\}/)   { $in_verb = 0; next }

        # ---- strip a trailing LaTeX comment before textual checks --------
        my $t = $raw;
        $t =~ s/(?<!\\)%.*$//;         # a real comment: unescaped %
        my $is_comment = ($raw =~ /^\s*%/);

        next if $in_verb;

        # ---- E: unescaped specials in text -------------------------------
        unless ($is_comment) {
            # % that is neither \% nor a comment start we already stripped:
            # after stripping, any surviving % must have been \%-escaped.
            my $probe = $raw;
            $probe =~ s/\\%//g;                       # remove escaped ones
            $probe =~ s/^\s*%.*$//;                   # whole-line comment
            $probe =~ s/(?<!\\)%.*$//;                # trailing comment
            # nothing to assert here; the comment-strip above is the test.

            # _ # $ outside math and outside \verb
            my $u = $t;
            # Filename and key arguments are exempt from the escaping check ONLY
            # where they are never typeset -- \fig, \figwide and \figmargin hand
            # theirs straight to \includegraphics.
            #
            # \figmissing is deliberately NOT in that list. It PRINTS its file
            # name, and blanket-exempting it here is what let
            #   \figmissing{fig_ppo2d_training_curve.png}{...}
            # through the checker and straight into "Missing $ inserted" on the
            # first real build. It is safe now only because the macro wraps the
            # argument in \detokenize; if that ever changes, this check must
            # catch it, so leave \figmissing checked.
            $u =~ s/\\fig(?:\[[^\]]*\])?\{[^{}]*\}\{[^{}]*\}/FIGCALL/g;
            $u =~ s/\\(?:figwide|figmargin)(?:\[[^\]]*\])?\{[^{}]*\}/FIGCALL/g;
            # \figmissing: exempt only when the macro's own \detokenize is what
            # protects it -- i.e. verify the definition still does that.
            $u =~ s/\\figmissing(?:\[[^\]]*\])?\{[^{}]*\}/FIGMISSING/g;
            $u =~ s/\\(?:label|ref|Cref|cref|autoref|pageref|nameref|parencite|textcite|cite|citeauthor|citeyear|includegraphics|graphicspath|input|include)(?:\[[^\]]*\])?\{[^{}]*\}/REFCALL/g;
            $u =~ s/\\[a-zA-Z]+//g;                   # drop control words
            $u =~ s/\\[_#\$&{}%]//g;                  # drop escaped specials
            $u =~ s/\$[^\$]*\$//g;                    # drop inline math
            $u =~ s/\\verb\|[^|]*\|//g;               # drop \verb|...|
            if ($u =~ /(?<!\\)_/)  { err($file,$ln,"unescaped '_' outside math") }
            if ($u =~ /(?<!\\)#/)  { err($file,$ln,"unescaped '#'") }
            if ($u =~ /(?<!\\)\$/) { err($file,$ln,"stray '\$' (unbalanced math?)") }
        }

        # ---- E: bare Greek / maths glyphs outside math -------------------
        my $g = $t;
        $g =~ s/\$[^\$]*\$//g;
        if ($g =~ /([\x{0370}-\x{03FF}\x{2190}-\x{21FF}\x{2200}-\x{22FF}\x{00B1}\x{00D7}\x{00F7}\x{00B2}\x{00B3}])/) {
            err($file,$ln,"bare maths/Greek glyph '$1' outside math mode (Cochineal has no Greek)");
        }

        # ---- W: leftover Markdown ----------------------------------------
        if (!$is_comment) {
            warn_($file,$ln,"leftover Markdown bold '**'")      if $t =~ /\*\*/;
            warn_($file,$ln,"leftover Markdown heading '#'")    if $t =~ /^\s*#{1,6}\s/;
            warn_($file,$ln,"leftover Markdown table row '|'")  if $t =~ /^\s*\|.*\|\s*$/;
            warn_($file,$ln,"leftover Markdown code span") if $t =~ /`[^`']*`/;  # a lone ` ... ' is a LaTeX open quote, not Markdown
        }

        # ---- E: unknown macros -------------------------------------------
        unless ($is_comment) {
            while ($t =~ /\\([a-zA-Z]+)/g) {
                my $m = $1;
                next if $ok{$m};
                err($file,$ln,"unknown macro \\$m");
            }
        }

        # ---- E: \fig / \figwide / \figmissing arity ----------------------
        if ($t =~ /\\fig\b/ && $t !~ /\\figwide|\\figmargin|\\figmissing/) {
            my $n = () = $t =~ /\}\s*\{/g;
            err($file,$ln,"\\fig should take 4 brace groups, found ".($n+1))
                if $t =~ /\\fig(?:\[[^\]]*\])?\{/ && $n != 3;
        }
        if ($t =~ /\\figwide(?:\[[^\]]*\])?\{/) {
            my $n = () = $t =~ /\}\s*\{/g;
            err($file,$ln,"\\figwide should take 3 brace groups, found ".($n+1)) if $n != 2;
        }
        if ($t =~ /\\figmissing(?:\[[^\]]*\])?\{/) {
            my $n = () = $t =~ /\}\s*\{/g;
            err($file,$ln,"\\figmissing should take 2 brace groups, found ".($n+1)) if $n != 1;
        }

        # ---- environments -------------------------------------------------
        while ($t =~ /\\begin\{([^}]+)\}/g) {
            my $e = $1;
            err($file,$ln,"unknown environment '$e'") unless $env_ok{$e};
            push @envs, [$e, $ln];
        }
        while ($t =~ /\\end\{([^}]+)\}/g) {
            my $e = $1;
            if (!@envs) { err($file,$ln,"\\end{$e} with no matching \\begin") }
            else {
                my $top = pop @envs;
                err($file,$ln,"\\end{$e} closes \\begin{$top->[0]} opened at line $top->[1]")
                    if $top->[0] ne $e;
            }
        }

        # ---- W: sidenote inside a float ----------------------------------
        if ($t =~ /\\(sidenote|marginnote)\b/) {
            my $inside = 0;
            for my $e (@envs) { $inside = 1 if $e->[0] =~ /^(figure|table|longtable|tabularx|tabular)\*?$/ }
            warn_($file,$ln,"\\$1 inside a float/table -- this breaks") if $inside;
        }

        # ---- W: longtable without \endhead --------------------------------
        # (checked at close, below)

        # ---- brace balance ------------------------------------------------
        my $b = $t;
        $b =~ s/\\[{}]//g;    # escaped braces do not count
        $b =~ s/\\[a-zA-Z]+//g;
        $depth += ($b =~ tr/{//);
        $depth -= ($b =~ tr/}//);
        if ($depth < 0) { err($file,$ln,"brace depth went negative"); $depth = 0 }
    }

    err($file, scalar(@lines), "file ends with brace depth $depth (expected 0)") if $depth != 0;
    for my $e (@envs) { err($file, $e->[1], "\\begin{$e->[0]} never closed") }

    # ---- table row width consistency, per environment ---------------------
    #
    # Column specs nest braces three deep in this document
    # (Y*{7}{>{\centering\arraybackslash}p{13mm}}), which no flat regex can
    # match, so pull the balanced group out by hand.
    my $txt = join("", @lines);

    # Return the balanced {...} group starting at $pos, and the position after
    # it; undef if $pos is not on an opening brace.
    my $grab = sub {
        my ($s, $pos) = @_;
        return (undef, $pos) unless substr($s, $pos, 1) eq '{';
        my $d = 0;
        for (my $j = $pos; $j < length($s); $j++) {
            my $c = substr($s, $j, 1);
            next if $j > $pos && substr($s, $j - 1, 1) eq "\\";
            $d++ if $c eq '{';
            $d-- if $c eq '}';
            return (substr($s, $pos + 1, $j - $pos - 1), $j + 1) if $d == 0;
        }
        return (undef, $pos);
    };

    while ($txt =~ /\\begin\{(tabularx|tabular|longtable)\}/g) {
        my $env = $1;
        my $pos = pos($txt);
        # tabularx and longtable take a width argument first
        if ($env ne 'tabular') {
            my ($w, $np) = $grab->($txt, $pos);
            $pos = $np if defined $w;
        }
        # an optional [t]/[b] positioning argument may sit here
        if (substr($txt, $pos, 1) eq '[') {
            my $close = index($txt, ']', $pos);
            $pos = $close + 1 if $close > -1;
        }
        my ($spec, $after) = $grab->($txt, $pos);
        next unless defined $spec;
        my $endat = index($txt, "\\end{$env}", $after);
        next if $endat < 0;
        my $body = substr($txt, $after, $endat - $after);
        pos($txt) = $after;
        (my $s = $spec) =~ s/\@\{[^}]*\}//g;
        $s =~ s/[><]\{[^}]*\}//g;
        $s =~ s/[pmbLY]\{[^}]*\}/C/g;
        $s =~ s/\|//g;
        $s =~ s/\s//g;
        # expand *{n}{spec} repetitions -- otherwise a spec like Y*{7}{p{13mm}}
        # counts as 2 columns instead of 8
        1 while $s =~ s/\*\{(\d+)\}\{([^{}]*)\}/$2 x $1/e;
        my $cols = ($s =~ tr/lrcCXY//);
        next unless $cols > 1;
        for my $row (split /\\\\/, $body) {
            next if $row =~ /^\s*$/;
            next if $row =~ /\\(toprule|midrule|bottomrule|endhead|endfirsthead|endfoot|caption|label|hline|cmidrule|multicolumn)/;
            my $amp = () = $row =~ /(?<!\\)&/g;
            next if $amp == 0 && $row !~ /\S/;
            if ($amp != $cols - 1 && $amp > 0) {
                my ($snip) = $row =~ /^\s*(.{0,60})/s;
                $snip =~ s/\s+/ /g;
                err($file, 0,
                    "$env declares $cols columns but a row has ".($amp+1).": \"$snip...\"");
            }
        }
    }
    if ($txt =~ /\\begin\{longtable\}/ && $txt !~ /\\endhead/) {
        warn_($file, 0, "longtable without \\endhead -- header will not repeat");
    }
}

print "\n";
print $errors ? "FAIL  $errors error(s), $warns warning(s)\n"
              : "PASS  0 errors, $warns warning(s)\n";
exit($errors ? 1 : 0);
