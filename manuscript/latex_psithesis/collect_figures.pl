#!/usr/bin/perl
# Collect every figure the converted .tex files actually reference, and report
# which exist. Run from manuscript/latex_psithesis.
use strict;
use warnings;
use File::Copy qw(copy);

my $POOL = "../figures";
my $DEST = shift(@ARGV) or die "usage: collect_figs.pl <dest-dir>\n";
mkdir $DEST unless -d $DEST;

my %want;
for my $f (glob("chapters/*.tex appendices/*.tex front/*.tex")) {
    open(my $fh, "<:encoding(UTF-8)", $f) or die "$f: $!";
    local $/;
    my $t = <$fh>;
    close $fh;
    # \fig{width}{name}{caption}{label}  and  \figwide{name}{caption}{label}
    while ($t =~ /\\fig(?:\[[^\]]*\])?\{[^{}]*\}\{([^{}]+)\}/g)      { $want{$1} = 1 }
    while ($t =~ /\\figwide(?:\[[^\]]*\])?\{([^{}]+)\}/g)            { $want{$1} = 1 }
    while ($t =~ /\\figmargin(?:\[[^\]]*\])?\{([^{}]+)\}/g)          { $want{$1} = 1 }
}

my (@ok, @missing);
for my $stem (sort keys %want) {
    my $found = 0;
    for my $ext (qw(.png .pdf .jpg .jpeg .svg)) {
        for my $dir ($POOL, "$POOL/auto") {
            my $src = "$dir/$stem$ext";
            if (-f $src) {
                copy($src, "$DEST/$stem$ext") or die "copy $src: $!";
                push @ok, "$stem$ext";
                $found = 1;
                last;
            }
        }
        last if $found;
    }
    push @missing, $stem unless $found;
}

print "figures referenced: ", scalar(keys %want), "\n";
print "copied  : $_\n" for @ok;
print "MISSING : $_\n" for @missing;
print "\n", scalar(@ok), " copied, ", scalar(@missing), " missing\n";
