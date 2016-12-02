#!/usr/bin/perl -w

# written by: Shawn Manuel
# zID: z5018876
# Tutor: Fred
# Lab: Wednesday 12-3pm

# This program converts a perl script to python syntax in the areas of:
#  - variable assignment with +-/* operators
#  - print statements
#  - if-elsif-else statements
#  - while loops
#  - foreach loops
#  - reading from STDIN
#  - perl regex substitution

# FUNCTION DECLARATIONS
#  - @python = translate_statements(@perl) : takes in an array of perl and calls other
#                                             functions to translate parts of it
#  - @variables = get_variables($line)     : returns an array of $variables on the $line
#  - $line = translate_variable_assignment($line)  : returns a $line translation of
#                                                     assigning a value to perl variable
#  - $line = translate_print_statement($line)      : returns a $line translation of
#                                                     printing strings or $variables in perl
#  - @array = translate_if(@array)         : returns an array of a complete translated if script
#  - @array = translate_while(@array)      : returns an array of a complete translated while script
#  - @array = translate_foreach(@array)    : returns an array of a complete translated foreach script
#  - #$line = comment_out($line)           : returns a $line with a # in front

# DEBUG flags to print DEBUG output
$DEBUG_MAIN = 0;
$DEBUG_PRINT = 0;
$DEBUG_IF = 0;
$DEBUG_WHILE = 0;
$DEBUG_VARR_ASSIGN = 0;
$DEBUG_FOREACH = 0;

# GLOBAL REGEX
$header = qr/^#!\/usr/;       # the #!/usr/bin header
$var_name = qr/\w[\w\d]*/;    # a variable name must start with a character and then
                                 # can contain any alphanumeric characters after that
$if_condition = qr/[^\(\)]*/; # an if condition is defined as anything not a parenthesis
$regex = qr/[^\/]*/;          # a regex inside a perl match can be anything but a '/'
$regex_match = qr/(.?)\/($regex)\/($regex)\/(g?)/; # perl match format of s/regex/regex/g


# GLOBAL VARIABLES
$indent_size = "    ";  # a global var for the number of spaces in a tab
$indent = 0;            # a counter for the number of indents to put on certain lines
#%variables = {};       # a hash to hold the variable names to distinguish from strings
#%import = {};          # a hash to hold the required things to import

while (@my_perl = <>){

   print "=" x 20, " Full perl input is:\n", join("", @my_perl), "\n" if ($DEBUG_MAIN);
   
   # translate #! line
   if ($my_perl[0] =~ /$header/) {
      $py_header = "#!/usr/local/bin/python3.5 -u\n";
      shift @my_perl;
   }

   # translating the main body of the python
   @python = translate_statements(@my_perl);
   print "=" x 20, " Python body translated is:\n", join("", @python),"\n" if ($DEBUG_MAIN);

   # add the library items to import if there are any
   @to_import = keys %import;
   $import_header = (@to_import) ? "import ".join(', ',@to_import)."\n" : "";
   print "=" x 20, " Python imports translated is: ", $#to_import+1,"\n" if ($DEBUG_MAIN);

   # combining the three segments to form the translated python script
   @complete_python = ($py_header,$import_header,@python);
   
   print join("", @complete_python);
}

# function that takes in any array of a complete perl script from opening '{' to closing '}'
# level and calls individual functions for different perl operators as:
#  - Variable assignment                  : $var_name = ... [+-/*] ...
#  - Variable shorthand incrementing      : $var_name++ --> var_name += 1
#  - print statements                     : print "string or $variable"
#  - if/while statements                  : if/while (condition) { sub_array }
#  - foreach statements                   : foreach $var_name ($array_name)  or
#                                         : foreach $var_name (start..end)
#      - The if/while/foreach translator
#        passes the complete if/while script
#        from the condition line to closing '{'
#
#  - else/elsif conditionals of if        : } else {    or
#                                         : } elsif (condition) {
#
#  - Converting 'last' and 'next'         : last --> break
#                                         : next --> continue
#  - chomp function                       : chomp $var --> var.rstrip();
sub translate_statements {
   my @array = @_;         # The array with the perl
   my $index = 0;          # tracking the current in array line being translated
   my @translated = ();    # the python array to return
   
   print "=" x 20, " Passed into tr_st:\n", join("", @array),"\n", "=" x 20, "\n" if ($DEBUG_MAIN);
   
   # Going through each line of the array until the end
   while ($index <= $#array) {
      my $line = $array[$index];    # setting $line
      $line =~ s/^\s*//;            # getting rid of white space
      chomp $line;
      
      print "> In translate statement, translating $line at index $index\n" if ($DEBUG_MAIN);
      
      # Go through the $line and pick out any $variables from it and store in a
      # hash to confirm it exists when printing it before eliminating the '$'
      #  --> calls the get_variables sub routine
      #
      foreach $variable (get_variables($line)){
         $variables{$variable}++;
         print "\n>> Added variable: $variable\n" if ($DEBUG_MAIN)
      }
   
      # assigning variables as $var = ...
      #  --> calls the translate_variable_assignment sub routine
      #
      if ($line =~ /^[\$|\@]($var_name)\s*[+-]*=\s*(.*);/) {
         $translated_var_assign = translate_variable_assignment($line);
         push @translated, "$indent_size"x$indent."$translated_var_assign\n";
         print ">> Exited variable assignment with '$translated_var_assign'\n" if ($DEBUG_MAIN);
         
      # changing the ++ and -- incrementers to += or -= 1
      #
      } elsif ($line =~ /^\$($var_name)\s*([+-])[+-]\s*;$/){
         $translated_increment = "$1 $2= 1";
         push @translated, "$indent_size"x$indent.$translated_increment."\n";
         print ">> Exited incrementer converter with '$translated_increment'\n" if ($DEBUG_MAIN);
         
      # The whole if, while or foreach script is passed as an array to the appropriate translator
      #  --> calls translate_if        if it is an if statement
      #  --> calls translate_while     if it is a while loop
      #  --> calls translate_foreach   if it is a foreach loop
      #
      } elsif ($line =~ /^(if|while)\s*\(.*\)\s*{/ || $line =~ /^(foreach)\s*(\$$var_name)\s*\(.*\)\s*{/){
         $type = $1;    # whether it is 'if' , 'while' or 'foreach'
         @loop = ();    # the sub array to send to the function
         print ">> $type loop at index $index\n" if ($DEBUG_WHILE || $DEBUG_IF || $DEBUG_FOREACH);
         
         # adding the if or while statement to a new array using '{' and '}' as line boundaries
         my $nested = 0;   # accounting for nested if/while/foreach loops inside the parent '{ }'
         my $i = $index;   # setting counter for sub array elemebts
         for ($i = $index; $i <= $#array; $i++) {
            
            # Adjusting counter for nesting
            $nested++ if ($array[$i] =~ /{/);
            $nested-- if ($array[$i] =~ /}/);
            
            print ">>> i in loop is $i and nested is $nested\n" if ($DEBUG_MAIN);
            
            push @loop, $array[$i]; # adding lines for the sub array
            
            # break when it reaches the while/if/foreach end bracket and it's not a nested one
            last if ($array[$i] =~ /}$/ && $nested == 0);
         }
         
         $index = $i;   # adjusting the main index to be the last element passed in as the loop
         push @translated, "translate_$type"->(@loop);  # calling the appropriate function based on $type
         
      # if it's the one line if statement, convert it to if array then send to translate_if
      } elsif ($line =~ /^\s*(.*)\s*if\s*\((.*)\)\s*;/){
         $condition = $2;
         $execute = $1;
         @to_translate = ("if ($condition){\n","$execute;\n","}\n");
         push @translated, translate_if(@to_translate);
         
      # if it is an else condition, just convert it
      } elsif ($line =~ /^}\s*(else|elsif)\s*\(?($if_condition)?\)?\s*{/){
         $condition = translate_variable($2);
         $translate = ($condition) ? "elif $condition:" : "else:";
         push @translated, "$indent_size"x($indent-1).$translate."\n";
      
      # Print statements can be passes to the print translator
      #  --> calls the translate_print_statement sub routing
      #
      } elsif ($line =~ /^print\s*(.*)\s*;?/) {
         $translated_print = translate_print_statement($line);
         push @translated, "$indent_size"x$indent.$translated_print;
         print ">> Exited print with '$translated_print'\n" if ($DEBUG_MAIN);
         
      # changing last to break and next to continue
      } elsif ($line =~ /^(last)\s*;/ || $line =~ /^(next)\s*;/){
         $translate = ($1 eq "last") ? "break" : "continue";
         push @translated, "$indent_size"x$indent.$translate,"\n";
      
      # checking for chomping
      } elsif ($line =~ /^chomp\s*(.*)\s*;/){
         $var = translate_variable($1);
         $translate = "$var = $var.rstrip(\\n)\n";
         push @translated, "$indent_size"x$indent.$translate;
         print ">> Entered chomp and returned '$translate'\n" if ($DEBUG_MAIN);
      
      # Blank & comment lines can be passed unchanged
      } elsif ($line =~ /^$/ || $line =~ /^#/) {
         push @translated, "$indent_size"x$indent.$line."\n";
         print ">> New line\n" if ($DEBUG_MAIN);
         
      # Lines we can't translate are turned into comments
      } else {
         push @translated, "$indent_size"x$indent.comment_out($line);
      }
   
      $index++; # go to next line
   }

   return @translated;
}


# function that takes in a $line and returns an array of any variables on that line
sub get_variables {
   my $line = shift;
   my @variables = ();     # array to return
   
   # only count variables being assigned, not printed
   unless ($line =~ /^print\s*(.*)\s*;?/){
      # searching for each word starting with a '$' and adding it to an array
      foreach $variable ($line =~ /\$$var_name/g){
         push @variables, $variable;
      }
   }
   
   return @variables;
}

# function that removes all '$' and '@' from a variable or array in $line
sub translate_variable {
   my $variable_line = shift;
   $import{"sys"}++ if ($variable_line =~ s/\$ARGV/sys.argv/g);
   $variable_line =~ s/\$//g;
   $variable_line =~ s/\@//g;
   return $variable_line;
}

# function that takes in a string of a variable, an operator and a variable
# assignment together and translates it to python
sub translate_variable_assignment {
   my $line = shift;
   print "\nEntered tr_va_as with '$line'\n" if ($DEBUG_VARR_ASSIGN);
   
   # isolate dependent variable, operator and independent variables if they exist
   if ($line =~ /^\s*([\$|\@])($var_name)\s*([=<>!~]+|eq)\s*([^;]*);?/){
      my $var_type = $1;
      my $dependent = translate_variable($2);
      my $operator = $3;
      my $independents = translate_variable($4);
      
      print "$dependent, $operator, $independents, \n" if ($DEBUG_VARR_ASSIGN);
      
      # case where <STDIN> is used for a static variable input
      if ($operator eq "=" and $independents =~ /<STDIN>/) {
         $import{"sys"}++;
         if ($var_type eq "\@"){
            $independents = "sys.stdin.readlines()";
         } elsif ($var_type eq "\$"){
            $independents = "sys.stdin.readline()";
         }
         # case where it is the perl string comparator 'eq', python only uses '=='
      } elsif ($operator eq "eq"){
         $operator = "==";
         
         # case where it is a regex substitution
      } elsif ($operator eq "=~"){
         $import{"re"}++;
         $operator = "=";
         $independents =~ /$regex_match/; # capturing the elements of (s)/(regex)/(regex)/(g);
         # see global variable at top
         $action = $1;
         $regex_from = $2;
         $regex_to = $3;
         $global = $4;
         
         # case for substituting
         if ($action eq "s"){
            $independents = "re.sub(r\'$regex_from\', \'$regex_to\', $dependent)";
         }
         
         print "$action, $regex_from, $regex_to, $global \n" if ($DEBUG_VARR_ASSIGN);
      }
      
      # recombine the elements adjusted above
      $translated_variable_assignment = $dependent." ".$operator." ".$independents;
      
      # if it's not in that form, just translate it by removing '$'
   } else {
      $translated_variable_assignment = translate_variable($line);
   }
   
   return $translated_variable_assignment;
}

# function that takes in a perl print statement of the form: print "string or $var"
# and returns the translated print function in python
sub translate_print_statement {
   my $line = shift;
   print "\n> Entered print with '$line'\n" if ($DEBUG_MAIN);
   
   # isolating the phrase to print
   $line =~ /\s*print\s*(.*)\s*;/;
   $to_print = $1;
   
   # check if there's a new line argument at the end of the print statement
   if ($to_print =~ /,\s*\"\\n\"\s*$/){   # if the new line is at the end of a string
      $explicit_new_line = 1;
      $to_print =~ s/,\s*\"\\n\"\s*$//;
   } elsif ($to_print =~ /\\n\"\s*$/){    # if the new line is a separate print argument
      $explicit_new_line = 1;
   } else {
      $explicit_new_line = 0;
   }
   
   # split each argument to print (separated by ',') in an array
   my @print_args = split(/,/,$to_print);
   print ">> print arguments: ", join("|",@print_args), "\n" if ($DEBUG_PRINT);
   
   # translate each argument separately
   my @translated_args = ();
   while (my $line = shift @print_args){
      
      # if the line is a string, then search each word and separate
      # sub strings from variables
      if ($line =~ /^\"(.*)\"\s*/){
         
         # split each line to print if there are any new lines
         my @new_lines = split(/\\n/,$1);
         print ">> The new line is: ", join(",",@new_lines), "\n" if ($DEBUG_PRINT);
         
         my @translated_new_lines = ();   # holding multiple new lines within middle of print
         foreach $new_line (@new_lines){
            @words = split(" ",$ new_line); # isolating the words within quotes
            
            # initializing array for the translated words in the line
            my @translated_words = ();
            foreach $word (@words){
               print ">>> raw word: '$word'\n" if ($DEBUG_PRINT);
               
               # check if it matches a variable in the variables hash
               if (!defined($variables{$word})){
                  
                  # if it isn't a variable it's a sub string or environment variable
                  if ($word =~ /\$ARGV\[(.*)\]/){     # case for environment ARGV variable
                     $import{"sys"}++;
                     $argv_index = translate_variable($1);
                     $word = "sys.argv[$argv_index + 1]";
                  } else {                            # otherwise treat it as a string
                     $word = "\"$word\"";
                  }
                  
               # if it is a variable, translate it by removing the '$'
               } else {
                  
                  $word = translate_variable($word);
               }
               
               # adding each word to the array
               push @translated_words, $word;
            }
            
            if ($DEBUG_PRINT){
               print ">> individual words are:\n";
               foreach $translated_word (@translated_words){
                  print "\t- $translated_word -\n";
               }
            }

            # going through the individual words and joining the
            # adjacent substrings
            my @adj_strings = ();      # holding the substrings adjacent to each other
            my $joined_string = "";    # to hold the combined @temp_string when variable found
            my @final_string = ();
            foreach $translated_word (@translated_words){
               # case where it is a substring, then add it to the adj
               if ($translated_word =~ /^"(.*)"/){
                  push @adj_strings, $1; # just add it to the temp string array
                 
               # case where it is a variable, then join the temp string with spaces and
               # push it to the array with the variable after it
               } else {
                  # if there were any adjacent strings before variable, join them into
                  # one string and add to final string
                  if (@adj_strings){
                     $joined_string = join(" ", @adj_strings);
                     push @final_string, "\"$joined_string\"";
                  }
                  
                  # add the variable next
                  push @final_string, $translated_word;
                  
                  @adj_strings = ();  # initialize the temp string for the next lot
               }
            }
            
            # joining the last substring following the last variable
            if (@adj_strings){
               $joined_string = join(" ", @adj_strings);
               push @final_string, "\"$joined_string\"";
            }
            
            print ">> The final new line is:", join(",",@final_string), "\n" if ($DEBUG_PRINT);
            
            # combining all
            $translated_new_line = join(",",@final_string);
            push @translated_new_lines, $translated_new_line;
         }
         
         $translated_line = join(",\"\\n\",",@translated_new_lines);
      
      # if it is the join operator, adjust accordingly
      } elsif ($line =~ /join\([\'\"](.*)[\'\"]\s*/){
         $delimiter = $1;                    # what to put between elements to join
         $array_to_join = shift @print_args; # the array to join will be in the next element of print args
         $array_to_join =~ s/\)\s*$//;       # getting rid of bracket at end
         $array_to_join =~ s/\s//;           # getting rid of white space
         
         if ($array_to_join =~ /\@ARGV/){    # case where the environment variable is being joined
            $array_to_join = "sys.argv[1:]";
            $import{"sys"}++;                # importing required python library
         }
         
         # setting python equivalent of join command
         $translated_line = "\'$delimiter\'\.join($array_to_join)";
         
      # if it isn't a string, then just pass it through
      } else {
         $translated_line = translate_variable($line);
      }
      
      push @translated_args, $translated_line;
   }

   # joining the print arguments by the original commas separating them
   $translated = join(",",@translated_args);
   print ">> the translated line is: ", $translated, "\n" if ($DEBUG_PRINT);
   
   # determining which print command to wrap the line to print depending on new line at end
   if ($explicit_new_line == 1){    # case where there is a new line, use python's print with built \n
      $to_print = "print($translated)\n";
   } else {                         # otherwise use the raw python print function
      $to_print = "sys.stdout.write($translated)\n";
      $import{"sys"}++;
      # alternative: $to_print = "print($translated, end=\"\")\n";
   }
   
   print "reached the end of print with '$to_print' \n" if ($DEBUG_MAIN);
   return $to_print;
}

# function which returns a translated if statement by taking in the
# perl if statement as an array
sub translate_if {
   my @my_if = @_;      # storing the complete perl if script
   my @py_if = ();      # the python equivalent to return
   
   print ">> Array passed into tr_if\n", join("",@my_if) if ($DEBUG_IF);
   
   # translating if condition in the recognized format
   if ($my_if[0] =~ /\s*if\s*\(($if_condition)\)\s*{/){
      my $condition = translate_variable_assignment($1); # isolating if condition in python
      push @py_if, "$indent_size"x$indent."if $condition:\n";
   }
      
   # Isolating the body of the if statement withing the parent '{ }'
   @statements = splice @my_if, 1, $#my_if -1;
   
   # Pass it to translate_statements with the required indent
   $indent++;
   push @py_if, translate_statements(@statements);
   $indent--;
   
   print ">> Translated if\n", @py_if, "\n" if ($DEBUG_IF);
   
   return @py_if;
}

# function which returns a translated while loop by taking in the
# perl if statement as an array
sub translate_while {
   my @my_while = @_;   # the complete perl while script
   my @py_while = ();   # the python while to return
   
   print "\n>> Array passed into tr_wh\n", join("",@my_while), if ($DEBUG_WHILE);
   
   # translating while condition in the recognized format
   if ($my_while[0] =~ /\s*while\s*\((.*)\)\s*{/){
      my $condition = $1;
      
      print ">> in while, condition is '$condition'\n" if ($DEBUG_WHILE);
      # checking the case where the it is going through the <> or <STDIN> operator,
      # then we need to use the fileinput or sys library for python
      if ($condition =~ /\$(\w+)\s*=\s*<(STDIN)?>/){
         $element = $1; # getting the name of the variable to hold each input
         
         # check if the STDIN exists withing the <>
         if ($2 && $2 eq "STDIN"){  # case where it is <STDIN>
            $import{"sys"}++;
            $while_header = "for $element in sys.stdin:\n";
         } else {                   # case where it is <>
            $import{"fileinput"}++;
            $while_header = "for $element in fileinput.input():\n";
         }
         
      # otheraise it is a normal while condition
      } else {
         $condition = translate_variable_assignment($condition);
         $while_header = "while $condition:\n";
      }
      
      push @py_while, "$indent_size"x$indent.$while_header;
   }
      
   
   # Isolating the body of the while statement withing the parent '{ }'
   @statements = splice @my_while, 1, $#my_while -1;
      
   # Pass it to translate_statements with the required indent
   $indent++;
   push @py_while, translate_statements(@statements);
   $indent--;
   
   print "\n>> Translated while\n", @py_while, if ($DEBUG_WHILE);
   
   return @py_while;
}

# function which takes in an array of a complete for loop and returns an array of
# the translated for loop in python
sub translate_foreach {
   my @my_foreach = @_;    # perl for loop array
   my @py_foreach = ();    # python for loop array initialized
   
   print "\n>> Array passed into tr_fo\n", join("",@my_foreach), if ($DEBUG_FOREACH);
   
   # Checking that the start of the array is the correctly formatted header
   if ($my_foreach[0] =~ /\s*foreach\s*(\$$var_name)\s*\((.*)\)\s*{/){
      my $element = translate_variable($1);
      my $array_to_cycle = $2;
      
      # case where it is an environment variable to cycle through
      if ($array_to_cycle =~ /\@ARGV/){
         $array_to_cycle = "sys.argv[1:]";
         $import{"sys"}++;
         
      # otherwise if it's a range like (start..end)
      } elsif ($array_to_cycle =~ /([^\.]+)\.\.([^\.]+)/){
         $start = $1;
         $end = $2+1;
         # if the end parameter refers to the last index of array shorthand of $#array
         if ($end =~ /^\$#($var_name)/){
            $foreach_array = $1;
            $foreach_array = "sys.argv" if ($foreach_array eq "ARGV");
            $end = "len($foreach_array) - 1";
         }
         $array_to_cycle = "range($start, $end)";
      }
      
      push @py_foreach, "$indent_size"x$indent."for $element in $array_to_cycle:\n";
   }
      
   # Isolating the body of the foreach statement withing the parent '{ }'
   @statements = splice @my_foreach, 1, $#my_foreach -1;
   
   # Pass it to translate_statements with the required indent
   $indent++;
   push @py_foreach, translate_statements(@statements);
   $indent--;
   
   print "\n>> Translated foreach\n", @py_foreach, if ($DEBUG_FOREACH);
   
   return @py_foreach;
}

# function that takes in a line as input and returns it commented
sub comment_out {
   my $line = shift;
   chomp $line;
   return "# $line\n";
}

# [1] http://perlmaven.com/splice-to-slice-and-dice-arrays-in-perl - splicing arrays



