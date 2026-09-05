#!/usr/bin/perl
# check_complete.pl -- did the conversion drop anything?
#
# check_tex.pl answers "would it compile". This answers the other half:
# "is it still the same document". It compares each .tex against the Markdown
# it came from on two axes that a dropped or summarised passage cannot fake:
#
#   * section and subsection counts must match exactly;
#   * running-word count must land within a tolerance band. LaTeX markup is
#     stripped before counting, so the two numbers are comparable. Below the
#     band means text went missing; well above usually means Markdown leaked in.
#
# Neither is proof. Both are cheap, deterministic and catch the failure that
# matters most here -- an agent quietly summarising a paragraph it found long.
#
# Usage: perl check_complete.pl

use strict;
use warnings;

my $SRC = "../draft_v5_en";
my $LO  = 0.90;   # tex/md word ratio floor
my $HI  = 1.12;   # ceiling

my @pairs = (
  ["body/01_introduction.md",                "chapters/chapter01.tex"],
  ["body/02_related_work.md",                "chapters/chapter02.tex"],
  ["body/03_methodology.md",                 "chapters/chapter03.tex"],
  ["body/04_domain_hazards_requirements.md", "chapters/chapter04.tex"],
  ["body/05_architecture_and_cage.md",       "chapters/chapter05.tex"],
  ["body/06_implementation.md",              "chapters/chapter06.tex"],
  ["body/07_training.md",                    "chapters/chapter07.tex"],
  ["body/08_experimental_evaluation.md",     "chapters/chapter08.tex"],
  ["body/09_sim_to_real_gap.md",             "chapters/chapter09.tex"],
  ["body/10_operational_validation.md",      "chapters/chapter10.tex"],
  ["body/11_discussion.md",                  "chapters/chapter11.tex"],
  ["body/12_conclusions.md",                 "chapters/chapter12.tex"],
  ["back/A_appendix_hazards.md",             "appendices/appendixA.tex"],
  ["back/B_appendix_requirements.md",        "appendices/appendixB.tex"],
  ["back/C_appendix_instruments.md",         "appendices/appendixC.tex"],
  ["back/D_appendix_odd.md",                 "appendices/appendixD.tex"],
  ["back/E_appendix_cage.md",                "appendices/appendixE.tex"],
  ["back/F_appendix_traceability.md",        "appendices/appendixF.tex"],
  ["back/G_appendix_positioning.md",         "appendices/appendixG.tex"],
  ["back/H_appendix_training.md",            "appendices/appendixH.tex"],
  ["back/I_appendix_campaign.md",            "appendices/appendixI.tex"],
  ["front/10_abstract.md",                   "front/abstract.tex"],
  ["front/15_preface.md",                    "front/preface.tex"],
  ["front/05_declaration.md",                "front/declaration.tex"],
  ["front/40_abbreviations.md",              "front/abbreviations.tex"],
);

sub slurp {
    my ($p) = @_;
    open(my $fh, "<:encoding(UTF-8)", $p) or return undef;
    local $/;
    my $s = <$fh>;
    close $fh;
    return $s;
}

sub words_md {
    my ($s) = @_;
    $s =~ s/^```.*?^```//gms;      # fenced code
    $s =~ s/<img[^>]*>//g;         # figure tags
    # Table CONTENT counts -- the appendices are almost entirely registers, and
    # dropping their rows here made every table-heavy file look inflated on the
    # LaTeX side. Only the alignment rows (|---|:-:|) are noise.
    $s =~ s/^\s*\|[\s|:-]*\|\s*$//gm;
    $s =~ s/[*_`#>\[\]()|-]/ /g;   # markup punctuation, hyphens included
    my @w = ($s =~ /(\S+)/g);
    return scalar @w;
}

# Known-good reasons a converted file legitimately counts fewer words than its
# source, none of which is content loss:
#   * an identifier collapses into a macro -- "SR-001" -> \sr{001};
#   * a Greek-lettered parameter becomes maths -- "theta_max" -> $\theta_{\max}$,
#     where BOTH name parts are control words and vanish from the count;
#   * "Appendix X" in the H1 becomes \chapter{}, with LaTeX supplying the word.
# The identifier-dense appendices sit near the floor for exactly these reasons;
# their table rows were counted directly and match one for one.

sub words_tex {
    my ($s) = @_;
    $s =~ s/^\s*%.*$//gm;                       # comments
    $s =~ s/\\begin\{(verbatim|lstlisting)\}.*?\\end\{\1\}//gs;
    $s =~ s/\\(label|ref|Cref|cref|includegraphics|graphicspath)\{[^{}]*\}//g;
    $s =~ s/\\[a-zA-Z]+\*?//g;                  # control words
    $s =~ s/[{}\\&\$~^_#-]/ /g;                 # LaTeX punctuation AND hyphens,
                                                # so that SC-PERT-04 tokenises
                                                # the same way on both sides
    my @w = ($s =~ /(\S+)/g);
    return scalar @w;
}

# ---------------------------------------------------------------------------
# Verified exceptions.
#
# These three files trip a threshold for a reason that was checked by hand and
# is NOT content loss. Each carries the evidence that settled it. Anything not
# listed here that trips a threshold is unexplained and needs a look.
# ---------------------------------------------------------------------------
my %expected = (
  'appendices/appendixC.tex' =>
    'section depth deliberately changed: the source hand-numbers 13 "##" headings '.
    'under 2 "#" divisions, so the "##" became subsections and LaTeX now numbers '.
    'them (the source numbering skipped C.3 and restarted at C.1)',
  'appendices/appendixF.tex' =>
    'identifier-dense: nearly every cell is an ID that collapsed into a macro. '.
    'Table rows counted directly: 47 in the Markdown, 47 in the LaTeX',
  'appendices/appendixG.tex' =>
    'every row label "Author and Author (year)" became \\textcite{key}, which is '.
    'the intended conversion; 21 rows in, 21 rows out',
);

my ($fail, $warn, $missing) = (0, 0, 0);
my $expected_hits = 0;
printf "%-34s %5s %5s  %5s %5s  %7s  %s\n",
       "file", "sec", "SEC", "sub", "SUB", "words", "verdict";
print "-" x 92, "\n";

for my $p (@pairs) {
    my ($md_rel, $tex_rel) = @$p;
    my $md  = slurp("$SRC/$md_rel");
    my $tex = slurp($tex_rel);

    if (!defined $md)  { printf "%-34s  %s\n", $tex_rel, "source missing: $md_rel"; next }
    if (!defined $tex) { printf "%-34s  %s\n", $tex_rel, "NOT CONVERTED YET"; $missing++; next }

    my $md_sec  = () = $md  =~ /^##\s+/gm;
    my $md_sub  = () = $md  =~ /^###\s+/gm;
    my $tx_sec  = () = $tex =~ /^\\section\{/gm;
    my $tx_sub  = () = $tex =~ /^\\subsection\{/gm;

    my $mw = words_md($md);
    my $tw = words_tex($tex);
    my $r  = $mw ? $tw / $mw : 0;

    my @notes;
    push @notes, "SECTIONS $md_sec->$tx_sec" if $md_sec != $tx_sec;
    push @notes, "SUBSECS $md_sub->$tx_sub"  if $md_sub != $tx_sub;
    push @notes, sprintf("WORDS %.2f", $r)   if $r < $LO || $r > $HI;

    my $verdict;
    if (@notes && $expected{$tex_rel}) {
        $verdict = "expected: " . join("; ", @notes);
        $expected_hits++;
    } elsif (@notes) {
        $verdict = join("; ", @notes);
        $fail++;
    } else {
        $verdict = "ok";
    }

    printf "%-34s %5d %5d  %5d %5d  %7s  %s\n",
           $tex_rel, $md_sec, $tx_sec, $md_sub, $tx_sub,
           sprintf("%.2f", $r), $verdict;
}

print "-" x 92, "\n";
print "$fail unexplained, $expected_hits verified exception(s), $missing not converted\n";
print "Section counts must match exactly. A words ratio below $LO means text was\n",
      "dropped; above $HI usually means Markdown leaked through.\n";
if ($expected_hits) {
    print "\nVerified exceptions -- checked by hand, not content loss:\n";
    for my $f (sort keys %expected) {
        printf "  %s\n      %s\n", $f, $expected{$f};
    }
}
exit($fail ? 1 : 0);
