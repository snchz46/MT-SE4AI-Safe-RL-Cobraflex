#!/usr/bin/perl
# check_refs.pl -- cross-file reference audit.
#
# check_tex.pl works one file at a time, so it cannot see the one defect that
# only exists between files: a \Cref whose \label is never defined. LaTeX turns
# those into "??" in the PDF and only a WARNING in the log, so they survive a
# successful build and reach the examiner. This catches them without a build.
#
# Usage: perl check_refs.pl chapters/*.tex appendices/*.tex front/*.tex

use strict;
use warnings;

my (%label_at, %ref_at);

for my $file (@ARGV) {
    open(my $fh, "<:encoding(UTF-8)", $file) or die "$file: $!";
    my $ln = 0;
    while (my $line = <$fh>) {
        $ln++;
        next if $line =~ /^\s*%/;
        (my $t = $line) =~ s/(?<!\\)%.*$//;

        while ($t =~ /\\label\{([^}]+)\}/g) {
            my $l = $1;
            push @{ $label_at{$l} }, "$file:$ln";
        }

        # The figure wrappers in misc/thesis-commands.tex build the label out
        # of their last argument -- ig{width}{file}{caption}{2.3} defines
        # fig:2.3 -- so a scan for \label alone reports every figure reference
        # as dangling. Take the last brace group of the call; the caption may
        # itself contain braces, so match it non-greedily up to end of line.
        #   ig[pl]{w}{file}{caption}{label}
        #   igwide[pl]{file}{caption}{label}   igmargin[off]{file}{caption}{label}
        while ($t =~ /\\fig(?:wide|margin)?(?:\\[[^\\]]*\\])?(?:\{(?:[^{}]|\{[^{}]*\})*\})+?\{([0-9A-Za-z.:_-]+)\}\s*$/gm) {
            push @{ $label_at{"fig:$1"} }, "$file:$ln";
        }
        while ($t =~ /\\(?:Cref|cref|ref|autoref|nameref|pageref)\{([^}]+)\}/g) {
            push @{ $ref_at{$1} }, "$file:$ln";
        }
    }
    close $fh;
}

my $problems = 0;

my @dangling = sort grep { !exists $label_at{$_} } keys %ref_at;
if (@dangling) {
    print "DANGLING REFERENCES -- these render as '??' in the PDF:\n";
    for my $r (@dangling) {
        printf "  %-14s referenced from %s\n", $r, join(", ", @{ $ref_at{$r} });
        $problems++;
    }
    print "\n";
}

my @dupes = sort grep { @{ $label_at{$_} } > 1 } keys %label_at;
if (@dupes) {
    print "DUPLICATE LABELS -- LaTeX keeps the last, references silently go wrong:\n";
    for my $l (@dupes) {
        printf "  %-14s defined at %s\n", $l, join(", ", @{ $label_at{$l} });
        $problems++;
    }
    print "\n";
}

my @unused = sort grep { !exists $ref_at{$_} } keys %label_at;
printf "%d labels defined, %d referenced, %d never referenced (harmless)\n",
       scalar(keys %label_at), scalar(keys %ref_at), scalar(@unused);

print $problems ? "FAIL  $problems problem(s)\n" : "PASS  no dangling or duplicate references\n";
exit($problems ? 1 : 0);
