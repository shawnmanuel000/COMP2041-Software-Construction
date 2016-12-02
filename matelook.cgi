#!/usr/bin/perl -w

# Matelook.cgi

# written by Shawn Manuel September-October 2016

# This program is a perl based CGI script that prints HTML to a server
# to serve up different pages relating to a social media website
# http://cgi.cse.unsw.edu.au/~cs2041/assignments/matelook/

# Library functions to use
use CGI qw/:all/;
use CGI::Carp qw/fatalsToBrowser warningsToBrowser/;
use File::Path qw(make_path remove_tree);
use File::Basename;
use POSIX qw(strftime);
use Math::Trig;
use Switch;

$CGI::POST_MAX = 1024*5000; # limiting the image file upload to 5mb

# define some global variables
$debug = 0;
$users_dir = "dataset-medium";
$tag_ids = 1;

# This is the main function which deals with the back end processing of action parameters
# which add or change the user's account elements stored in the dataset. It prints the
# Login page if a user hasn't been authenticated. The login page will authenticate a user
# by checking a matching username and password has been entered, then the user page will
# be displayed at the end following the actions of updating data based on parameters passed in.
sub main() {

   # print start of HTML ASAP to assist debugging if there is an error in the script
   print page_header();

   # Now tell CGI::Carp to embed any warning in HTML
   warningsToBrowser(1);

   # Print the title of the website as a standard element on all pages
   print_title();

   ########################## UPDATING ACCOUNT SETTINGS #############################

   # If the user chose to change their password, change their password entry
   # in the user.txt to the new password
   if (param('change_password') and param('new_pw') and param('conf_pw')){
      $new_pw = param('new_pw');
      if (param('new_pw') eq param('conf_pw') and !($new_pw =~ /[\/;'\\<>= ]/)){
         my $user = param('change_password');
         my $new_pw = param('new_pw');
         modify_file_param("$users_dir/$user/user.txt","password",$new_pw);
         param('pw_changed'=>"$user");
      }

   # If the user chose to suspend their account, create a suspend file or add suspension
   # status to the inactive.txt file
   } elsif (param('suspend_account')){
      my $suspend_user = param('suspend_account');

      # Creating the file inactivity.txt which holds the status of the account which
      # is to be counted as inactive due to either awaiting activation of suspension
      unless (-e "$users_dir/$suspend_user/inactive.txt"){
         open F, ">$users_dir/$suspend_user/inactive.txt" or die;
         close F;
      }

      # Changing the value of the status in inactivity.txt to suspended
      if (!modify_file_param("$users_dir/$suspend_user/inactive.txt","status","suspended")){
         add_param_to_file("$users_dir/$suspend_user/inactive.txt","status","suspended");
      }

   # If the user wants to unsuspend their account, remove the 'suspended' value from the
   # status parameter in inactive.txt which would be in their folder
   } elsif (param('unsuspend_account')){
      my $suspend_user = param('unsuspend_account');
      modify_file_param("$users_dir/$suspend_user/inactive.txt","status","");

   # If the user chose to delete their account, delete their zID directory in $users_dir
   } elsif (param('delete_account')){
      my $login_user = param('login_user');
      my $delete_user = param('delete_account');
      my $delete_path = "$users_dir/$delete_user";

      # Sanitizing the user id to be that of the login user and only of the form of a zID
      if ($delete_user =~ /z\d{7}/ and $delete_user eq $login_user){
         remove_tree($delete_path);
         param('login_user'=>"");
      }
   }

   ######################## LOGIN PAGE ACTIONS FROM BUTTONS #############################
   # The default is to display the login page if the user hasn't clicked on the 'create account'
   # or 'forgot password' buttons

   # If the user decided to create an account, take them to the sign up page
   if (param('create_account') || param('submit_account')){
      print_account_creation();

   # If they forgot their password, print the page which asks them for their username
   # or email to send them a password recovery email
   } elsif (param('forgot_password')){
      print_password_recovery();

   # Otherwise requiring users to supply their existing username and password to log in
   # if the login user has not been authenticated. The login page will then authenticate the user
   } elsif (!(param('login_user') and param('login_user') ne "")){
      print_login_page();
   }

   ######################## UPDATING USER DETAILS ACTIONS #############################
   # This updates the changed user details in user.txt which are displayed on the user's
   # profile and edited from the (edit) button on the login user page

   # Changing or uploading the user details of a current login user
   if (param('save_user_details') || param('add_course') || param('delete_course')){
      my $user = param('save_user_details') || param('add_course') || param('login_user');

      # Updating each of the user's details in the user.txt or creating an entry
      # for the parameter if it isn't already in the file
      foreach $param ('profile_text','full_name','program','home_suburb','birthday',
                                                   'home_latitude','home_longitude'){
         if (param($param)){
            my $param_value = param($param);
            $param_value =~ s/</&lt/g;
            $param_value =~ s/>/&gt/g;
            $param_value =~ s/[;\\<>=]//g;

            if(!modify_file_param("$users_dir/$user/user.txt",$param,$param_value)){
               add_param_to_file("$users_dir/$user/user.txt",$param,$param_value);
            }
         }
      }

      # The case where the user also chose to add a course, then take the individual
      # elements of the course text field and append it to the end of the course list
      # in the standard format
      if (param('add_course')){
         my $year = param('year');
         my $semester = param('semester');
         my $course = param('course');

         # Checking if the course elements were entered in correctly
         if ($year =~ /\d{4}/ and $semester =~ /\d/ and $course =~ /\w{4}\d{4}/){
            my $course_string = "$year S$semester $course";
            add_items($user,"courses",$course_string);
         } else {
            param('add_course'=>"invalid");
         }

      # Deleting the particular course from the user.txt file if they clicked on the
      # delete link next to the course in the 'change user details' page
      } elsif (param('delete_course')){
         my $course_to_delete = param('delete_course');
         delete_items($user, "courses", $course_to_delete);
      }
   }

   ######################## UPDATING PICTURE UPLOAD ACTIONS ###########################
   # Updating user's profile pic or background pic to what they uploaded and passed
   # into the script body or if they clicked remove to delete it
   foreach $param ("profile","background"){
      $file_param = "$param"."_pic";
      # Requiring both the file and the upload button to be clicked
      if (param("change_$param") && param("$file_param")){
         my $user = param("change_$param");

         # Specifying set path to save image to the user's directory
         my $save_path = "$users_dir/$user/$param.jpg";
         my $html = new CGI;
         my $image = $html->param("$file_param");

         # file handle for image
         my $image_handle = $html->upload("$file_param");

         open FILE, ">$save_path" or die "can't open : $!";
         binmode FILE;
         while (<$image_handle>) { print FILE;}
         close FILE;
         #sofurce: https://www.sitepoint.com/uploading-files-cgi-perl/

      # Otherwise deleting the file if they clicked the remove button
      } elsif (param("remove_$param")){
         my $user = param("remove_$param");

         # Perl function to delete a file
         unlink("$users_dir/$user/$param.jpg");
         #source: https://www.caveofprogramming.com/perl-tutorial/perl-file-delete-deleting-files-and-directories-in-perl.html
      }
   }

   ######################## UPDATING PRIVACY SETTINGS #############################
   # This saves the changes the user made to the privacy settings radio boxes under the
   # account settings tab or creates a privacy.txt file to save the new settings
   # from their default privacy settings

   if (param('save_privacy')){
      my $user = param('save_privacy');
      my $path = "$users_dir/$user/privacy.txt";

      # Opening a new file for privacy settings
      open F, '>'."$path" or die unless (-e $path);
      close F;

      # adding or updating each setting parameter passed in
      foreach $param ("posts","mate_list","profile_text","program","home_suburb",
                      "email","birthday","home_latitude","home_longitude","courses"){

         $param_value = param("privacy_$param");
         if(!modify_file_param("$users_dir/$user/privacy.txt",$param,$param_value)){
            add_param_to_file("$users_dir/$user/privacy.txt",$param,$param_value);
         }
      }
   }

   ######################## UPDATING MATES AND POSTS/COMMENTS #############################
   # This updates the user.txt for storing the mate requests made, which would then be
   # to the mates list when accepted, or deleting mates. It also updates the posts and
   # new comments that were made

   # This requires a login user to be defined when working with files in the user directory
   my $login_user = param('login_user') || "";

   if (existing_user($login_user)){

      ############################# UPDATING MATES  #############################
      # Updating mate requests sent or confirmed
      if (param('mate_request')){
         my $requested_mate = param('mate_request');
         # Add the new request to the existing mate_requests entry in user.txt
         if (find_in_file("$users_dir/$requested_mate/user.txt","mate_requests")){
            add_items($requested_mate, "mate_requests", $login_user);

         # Otherwise, create a new entry for the first request
         } else {
            add_param_to_file("$users_dir/$requested_mate/user.txt","mate_requests","[$login_user]");
         }

      # Updating mate request being confirmed by a login user
      } elsif (param('confirm_mate')){
         my $mate_confirmed = param('confirm_mate');

         # Removing the mate from the requests
         delete_items($login_user, "mate_requests", $mate_confirmed);

         # Adding the confirmed mate to the login user's mates list
         add_items($login_user, "mates", $mate_confirmed);

         # Adding the login user to the confirmed mates list
         add_items($mate_confirmed, "mates", $login_user);

      } elsif (param('delete_mate')){
         my $mate_to_unmate = param('delete_mate');

         # Removing the mate from the login user
         delete_items($login_user, "mates", $mate_to_unmate);

         # Removing the login user from the deleted mated
         delete_items($mate_to_unmate, "mates", $login_user);
      }

      ########################### UPDATING POSTS/COMMENTS  ##########################
      # Creating the post file if a post parameter was passed in
      if (param('post')){
         #creating post folder if it doesn't exist
         mkdir "$users_dir/$login_user/posts" unless (-e "$users_dir/$login_user/posts");

         #setting number of directory name
         my @posts = glob("$users_dir/$login_user/posts/*");
         my $num_posts = $#posts+1;

         # creating the new directory for the post
         my $dir = "$users_dir/$login_user/posts/$num_posts";
         mkdir $dir unless (-e $dir);

         make_post_file("$dir/post.txt",param('post'),$login_user);

      # Creating the comment file if a post parameter was passed in
      } elsif (param('comment')){
         my $comment_path = param('comment_path');

         #setting number of directory name
         mkdir "$comment_path/comments" unless (-e "$comment_path/comments");
         my @comments = glob("$comment_path/comments/*");
         my $num_comments = $#comments+1;

         # creating the new directory for the comment
         my $dir = "$comment_path/comments/$num_comments";
         mkdir "$dir" unless (-e "$dir");

         make_post_file("$dir/comment.txt",param('comment'),$login_user);

      # Deleting the directory with a comment or post where the link 'delete' was clicked
      } elsif (param('delete_comment') || param('delete_post')){
         my $delete_path = param('delete_comment') || param('delete_post');
         remove_tree($delete_path);
      }


      ########################### DISPLAYING USER PAGE  ##########################
      # Printing the user page after all the updates from the relevant parameters
      # have been processed provided that the login user is authenticated
      print_user_page();
   }

   # Completing HTML script with the trailer
   print page_trailer();
}

# This major function prints different variants of the user page depending on what the login user
# passed into the script by clicking on different elements. It maintains the same document format
# throughout which consists of:
#  - Nav bar: just under the title bar with links to
#        > Profile            - takes the user back to their profile
#        > News feed          - shows all the posts of the login user's mates with privacy permissions
#        > Search bar         - allows the user to search for mates or posts with privacy permissions
#        > Account settings   - takes the user to the change acc settings page
#        > Logout             - takes the user to the login page

#  - Aside: the vertical bar on the left which shows
#        > Mate status
#        > Display User Profile Pic
#        > Display User Details
#        > Display User mates

#  - Main: the vertical bar on the right for displaying
#        > Posts (default)
#        > Change profile picture and user details page (when (change) under the profile pic is clicked)
#        > Manage mates and see suggested mates page (when (manage mates) next to the mates title is clicked)
#        > Search results (when the user enters a search keyword for mates or posts)
#        > Change account settings and privacy page (when the user clicks on Account Settings)

sub print_user_page {
   my $login_user = param('login_user');
   my $display_user = param('display_user') || $login_user;

   # Printing out navigation bar with the profile, newsfeed, logout, account
   # settings and search features
   print "<nav>\n";
   print_nav_bar($login_user);
   print "</nav>\n";


   # Printing out the left aside bar with the profile pic, user details and mates list
   print "<aside>\n";
   print_mate_status($display_user,$login_user);
   print_display_pic($display_user,270);           # 270 pixel dimensions
   print_change_dp($display_user,$login_user);
   print_user_details($display_user,$login_user);
   print_user_mates($display_user,$login_user);
   print "</aside>\n";

   print  "<main>\n";

   # Displaying the caption if user has suspended their account
   if (inactive($login_user)){
      print_inactive_prompt();
   }

   # Printing the search field if the user submitted a search
   if (param('keywords') and !inactive($login_user)){
      print_search_results($login_user,$display_user);

   # Printing the account related settings like username and password and privacy
   } elsif (param('account_settings')){
      print_account_settings($login_user,$display_user);
      print_privacy_settings($login_user,$display_user);

   # Printing the text fields for the user to change their details
   } elsif (param('change_user_details')){
      print_change_user_pictures($login_user,$display_user);
      print_change_user_details($login_user,$display_user);

   # Printing the list of the user's mates to view or delete
   } elsif (param('manage_mates')){
      print_manage_mates($login_user,$display_user);
      print_suggest_mates($login_user,$display_user) unless (inactive($login_user));

   # Printing the posts made to the displayed user's profile
   } else {
      print_post_feed($login_user,$display_user);
      print_welcome() if (param('activate'));
   }

   print "</main>\n";

}

# ============================== Helper Functions =========================================

# This function displays the login textbox for the user to enter their
# username and password and checks it with the correct password in the
# user.txt
sub print_login_page {
   my $username = param('username') || '';
   my $activation = param('activate') || "";

   # First checking the username has been entered
   if ($username) {
      if (-e "$users_dir/$username") {
         my $correct_password = find_in_file("$users_dir/$username/user.txt","password");
         $correct_password =~ s/\s$//;

         # then checking it to the password
         my $password = param('password') || '';
         if ($password =~ /^$correct_password$/){
            # Checking if the user hasn't activated their account yet
            my $activity = inactive($username);
            chomp $activity;

            # If the user used the link, remove the inactive status
            if ($activity =~ /awaiting_activation=(.*)/){

               if ($activation eq $1){
                  modify_file_param("$users_dir/$username/inactive.txt","status","");
                  $inactive_prompt = "";
               } else {
                  $inactive_prompt = "Your account is still awaiting activation.
                                       Follow the link in your email to activate";
               }
            }

            # Log them in if they are now active
            unless ($inactive_prompt){
               param('login_user'=>$username);
               param('display_user'=>$username);
               print <<eof;
               <input type="hidden" name="login_user" value="$username" />
               <input type="hidden" name="display_user" value="$username" />
eof
            }
         } else {
            $incorrect_password = 1;
         }

      } else {
         $unknown_username = 1;
      }
   }

   # Setting the prompts to display if the user hadn't entered the login properly
   $incorrect_password_alert = !($incorrect_password || $unknown_username) ? "" : <<eof;
   <p style="color: red; padding-left: 20px"> Incorrect Username or Password </p>
eof

   $activation_alert = !($inactive_prompt) ? "" : <<eof;
   <p style="padding-left: 20px"> $inactive_prompt </p>
eof

   # Printing the login page again until the user is authenticated
   unless (param('login_user') || param('create_account')){
      print <<eof;
      <form action="" method="POST">
      <div class="matelook_user_details" align="centre">
      <input type="hidden" name="activate" value="$activation" />
      <table>
      <tr><td> Username: </td>
          <td> <input type="text" name="username" maxlength="8"/>  </td>
      </tr>
      <tr><td> Password: </td>
          <td> <input type="password" name="password" maxlength="16"/> </td>
          <td> <b> $incorrect_password_alert $activation_alert </b></td>
      </tr>
      <tr>
          <td> <input type="submit" value="Login" id="btn"/>
               <button type="submit" name="create_account" value="Sign Up"/>Sign Up</button> </td>
          <td> <button type="submit" name="forgot_password" value="Forgot"/>Forgot Password?</button> </td>
      </tr>
      </div>
      </form>
eof
   }
}

# This function prints the follow up page asking the new user to enter their account
# details to register and account and also checks that the account credentials are legal
sub print_account_creation {
   # Getting the parameters
   my $new_username = param('new_username') || "";
   my $new_password = param('new_pw') || "";
   my $confirm_password = param('conf_pw') || "";
   my $new_email = param('new_email') || "";

   # The characters that aren't allowed in a password
   my $illegal_chars = "/;`'\\<>= ";
   $new_email =~ s/</&lt/g;
   $new_email =~ s/>/&gt/g;

   # Checking their username was entered correctly
   if ($new_username =~ /z\d{7}/) {
      # Checking if it already exists
      if (-e "$users_dir/$new_username") {
         $new_username = "";
         $un_alert = "Username already exists";
      } else {
         $good_username = $new_username;
      }

   # If the username wasn't entered as a zid
   } elsif ($new_username){
      $un_alert = "Username must be a zID (eg. z5555555)";
      $new_username = "";

   # Otherwise if no zid was entered
   } else {
      $un_alert = "Please enter a zID username (eg. z5555555)" if (param('submit_account'));
   }

   # Checking for if password was even entered
   if (!$new_password){
      $pw_alert = "Please enter a password" if (param('submit_account'));

   # Checking that the password to confirm is the same as the first
   } elsif ($new_password ne $confirm_password){
      $pw_alert = "Passwords don't match";

   # Reject if the password contains illegal chars
   } elsif ($new_password =~ /[$illegal_chars]/){
      $pw_alert = "Password cannot contain any of (/;`'\\<>= )";
   } else {
      $good_password = $new_password;
   }

   # Checking for email already associated with account
   my $email_exists = 0;
   my @users = sort(glob("$users_dir/*"));
   foreach $user_dir (@users){
      $user_dir =~ /(z\d{7})/;
      my $user = $1;

      $check_email = find_in_file("$users_dir/$user/user.txt","email");
      if ($check_email =~ $new_email){
         $email_exists = 1;
         last;
      }
   }

   # Checking if an email was entered
   if (!$new_email){
      $em_alert = "Please enter an email" if (param('submit_account'));

   # Checking that the email is somewhat valid
   } elsif ($new_email =~ /@.*\.[com|edu|org](\.au)?/){
      if ($email_exists){
         $em_alert = "Email is already associated with an account";
      } else {
         $good_email = $new_email;
      }
   } else {
      $em_alert = "Invalid email";
   }


   # If the details were entered in the correct way, save them in a new directory and send
   # a confirmation email
   if ($good_username and $good_password and $good_email){
      my $user = $good_username;

      # Creating the directory for the new user
      my $dir = "$users_dir/$user/";
      mkdir $dir unless (-e $dir);

      # Creating the user.txt file
      open F, '>'."$dir/user.txt" or die;
      close F;

      # adding the username, password and email to it
      add_param_to_file("$users_dir/$user/user.txt","zid",$good_username);
      add_param_to_file("$users_dir/$user/user.txt","password",$good_password);
      add_param_to_file("$users_dir/$user/user.txt","email",$good_email);

      # creating the inactive.txt file which indicates whether the user has
      # activated their account through their email
      open F, '>'."$dir/inactive.txt" or die;
      close F;

      # making a random number to store in the inactive.txt and to attach to the
      # activation url so that the inactive status can be deactivated when they use the link
      my $activate = rand();

      # Setting the status to awaiting activation with the required code to match
      if (!modify_file_param("$users_dir/$user/inactive.txt","status","awaiting_activation=$activate")){
         add_param_to_file("$users_dir/$user/inactive.txt","status","awaiting_activation=$activate");
      }

      # Sending the email to the new user
      my $to = "$good_email";
      my $from = 'z5018876@student.unsw.edu.au';
      my $subject = 'Matelook Account Acvitation';
      my $message = <<eof;
      Click on this link to activate your account: $ENV{REDIRECT_SCRIPT_URI}?activate=$activate
eof
      send_mail($to,$from,$subject,$message);

      # Printing the buttons to return to the login page
      print <<eof;
      <div class="matelook_user_details" position="fixed" left="100px">
      <form action="" method="POST">
      You have been sent an activation email to $good_email to complete the activation process
      <button type="submit" name="login_user" value="" />Return to login</button>
      </form>
      </div>
eof

   # Print the form again with the appropriate prompts
   } else {

      # Defining the prompts to show if the user didn't enter the credentials in the right way
      $username_prompt = (!$un_alert) ? "" : <<eof;
      <b style="color: red"> $un_alert </b>
eof
      $password_prompt = (!$pw_alert) ? "" : <<eof;
      <b style="color: red"> $pw_alert </b>
eof
      $email_prompt = (!$em_alert) ? "" : <<eof;
      <b style="color: red"> $em_alert </b>
eof
      # Printing the new sign up form if they hadn't completed all sections in the right format
      print <<eof;
      <form action="" method="POST">
      <div class="matelook_user_details" position="fixed" left="100px">
      <table position="relative" left="100px">
      <tr>
         <td width="140px"> Username:    </td>
         <td width="170px"> <input type="text" name="new_username" value="$new_username" maxlength="16"/>  </td>
         <td>  $username_prompt </td>
      </tr>
      <tr>
         <td> Enter Password: </td>
         <td> <input type="password" name="new_pw" maxlength="16"/>  </td>
         <td>  $password_prompt </td>
      </tr>
      <tr>
         <td> Confirm Password: </td>
         <td> <input type="password" name="conf_pw" maxlength="16"/>  </td>
      </tr>
      <tr>
         <td width="140px"> Email:    </td>
         <td width="170px"> <input type="text" name="new_email" value="$new_email" maxlength="40"/>  </td>
         <td>  $email_prompt </td>
      </tr>
      </table>
      <button type="submit" name="submit_account" value="Sign Up" />Create Account</button>
      <button type="submit" name="login_user" value="" />Back</button>
      </div>
      </form>
eof
   }
}

# This function prints the follow up page asking the new user to enter their account
# details to register and account and also checks that the account credentials are legal
sub print_password_recovery {
   # Getting the parameters
   my $username = param('get_pw') || "";
   my $email = param('get_un') || "";

   # Setting the matched account details to send
   my $user_email = "";
   my $user_zid = "";
   my $user_pw = "";

   # Checking email of the provided username
   if ($username && !$email){
      # Validate the email if the username exists
      if (existing_user($username)){
         $user_email = find_in_file("$users_dir/$username/user.txt","email");
         $user_pw = find_in_file("$users_dir/$username/user.txt","password");
         $user_zid = $username;
      } else {
         $username_prompt = "The username entered isn't associated with any existing account";
      }

   # Checking each username for a match to the provided email
   } elsif ($email && !$username){
      my @users = sort(glob("$users_dir/*"));
      foreach $user_dir (@users){
         $user_dir =~ /(z\d{7})/;
         my $user = $1;

         $check_email = find_in_file("$users_dir/$user/user.txt","email");
         if ($check_email =~ $email){
            $user_zid = $user;
            $user_email = find_in_file("$users_dir/$user/user.txt","email");
            $user_pw = find_in_file("$users_dir/$user/user.txt","password");
            last;
         }
      }

      # if it wasn't found, print the alert prompt
      if (!$user_pw and !$user_email) {
         $email_prompt = "The email entered isn't associated with any existing account";
      }
   } else {
      $email_prompt = "Please enter only a username or email";
   }

   # Sending the email if all the credentials were validated
   if ($user_pw and $user_email and $user_zid){

      my $to = "$user_email";
      my $from = 'z5018876@student.unsw.edu.au';
      my $subject = 'Matelook Password Recovery';
      my $message = <<eof;
      Your username is: $user_zid
      Your password is: $user_pw
eof

      send_mail($to,$from,$subject,$message);

      print <<eof;
      <div class="matelook_user_details" position="fixed" left="100px">
      <form action="" method="POST">
      You have been sent an email to $user_email to recover your account details
      <button type="submit" name="login_user" value="" />Return to login</button>
      </form>
      </div>
eof

   # Otherwise, print the form again
   } else {

      print <<eof;
      <form action="" method="POST">
      <div class="matelook_user_details" position="fixed" left="100px">
      <input type="hidden" name="activate" value="$activation" />
      <table position="relative" left="100px">
      <tr>
         Enter your Username (zID) or email
      </tr>
      <tr>
         <td width="140px"> Username:    </td>
         <td width="170px"> <input type="text" name="get_pw"/>  </td>
         <td> <b style="color:red"> $username_prompt </b></td>
      </tr>
      <tr>
         <td width="140px"> Email:    </td>
         <td width="170px"> <input type="text" name="get_un" value="$new_email"/>  </td>
         <td> <b style="color:red"> $email_prompt </b></td>
      </tr>
      </table>
      <button type="submit" name="forgot_password" value="Recover" />Recover Password</button>
      <button type="submit" name="login_user" value="" />Back</button>
      </div>
      </form>
eof
   }
}

# This function prints the welcome post in blue on the new user's post feed to explain
# how their profile page works and how to get started with their account
sub print_welcome {
   print <<eof;
   <section style="background-color: #20415d; padding-left: 50px; padding-right: 50px; color:white">
   </p>
   <p>
      <b> Welcome to Matelook! </b>
   </p>
   <p>   This is your profile page. You have your navigation bar at the top where you can search for mates to add and also change your privacy settings in the account settings tab
   </p>
   <p>
      You can change your profile and background picture by clicking on (upload) under the default profile picture.
   </p>
   <p>
      You can also add your user details by clicking on (edit). Find mate suggestions by adding courses that you completed and also your latitude and longitude location. Click on the (manage mates) to access the suggested mates.
   </p>
   </section>
eof
}

# This function prints the text at the top of the main section telling the login user
# that their account is currently suspended and how to unsuspend it
sub print_inactive_prompt {
   print <<eof;
   <section style="background-color: #eeeeee; padding-left: 50px; padding-right: 50px">
   </p> <b>
   Your account is currently suspended. Other Matelook users will not be able to view or search
   for your profile and you will only be able to view your own profile. To unsuspend your account,
   go to Account Settings </b>
   </section>
eof
}

# This function takes a string of words in a message and converts any
# instances of zIDs to the corresponding full name by looking in the user.txt
sub id_to_name {
   my $comment = shift;
   @IDs = $comment =~ /z\d{7}/g;
   foreach $id (@IDs){
      $name = find_in_file("$users_dir/$id/user.txt","full_name");
      $comment =~ s/$id/$name/;
   }
   return $comment;
}

# This function converts the zids string of a message to be their full name with
# a link to that user's page
sub id_to_link {
   my $comment = shift;
   my $login_user = param('login_user');

   @IDs = $comment =~ /z\d{7}/g;
   foreach $id (@IDs){
      $name = find_in_file("$users_dir/$id/user.txt","full_name");
      $link = <<eof;
      <form action="" method="POST">
      <input type="hidden" name="login_user" value="$login_user" />
      <button type="submit" name="display_user" value="$id" class="button_small" display="inline">
      $name</button>
      </form>
eof
      $comment =~ s/$id/$link/;
   }
   return $comment;
}

# This function prints the title banner standard to all matelook pages and also checks
# for the existence of a background image in the CGI post that the user just uploaded
sub print_title {
  $display_user = param('display_user') || param('login_user');

   # Not displaying the background if they chose to remove the background
   if (-e "$users_dir/$display_user/background.jpg" && !param('remove_background')){
      $background = "background=\"$users_dir/$display_user/background.jpg\"";

   # getting their background image straight away and putting it in the body of the HTML
   # if they just uploaded it
   } elsif (param('change_background') && param("background_pic")){
      my $html = new CGI;
      my $image = $html->param("background_pic");

      $background = "background=\"$image\"";
   } else {
      $background = "";
   }

   print <<eof;
<body link="blue" $background>
<div class="banner">
matelook
</div>
eof
}

# This function displays the input user's profile pic by checking if it exists
# or if it doesn't it displays the generic empty profile pic
sub print_display_pic {
   my $curr_user = shift;
   my $dim = shift;
   my $img_src = image_existence($curr_user);
   print <<eof;
   <img src="$img_src" width="$dim" height="$dim">
eof
}

# This function prints the (change) link under the login user's profile picture for them
# to be taken to the upload or change their profile picture page
sub print_change_dp {
   my $display_user = shift;
   my $login_user = shift;

   $img_src = image_existence($display_user);
   $option = ($img_src =~ /chipinworld/) ? "upload" : "change";

   print <<eof if ($display_user eq $login_user);
   <form action="" method="POST">
   <div align="center">
   <input type="hidden" name="login_user" value="$login_user" />
   <input type="hidden" name="display_user" value="$login_user" />
   <button type="submit" name="change_user_details" value="$login_user" class="button_small">$option</button>
   </div>
   </form>
eof
}

# Helper function for print_display_pic where it returns the path to the user's profile
# pick if it exists, otherwise returns a link to an online generic empty profile pic
sub image_existence {
   my $user = shift;
   # If their image exists in the folder, use it
   if (-e "$users_dir/$user/profile.jpg") {
      $img_src = "$users_dir/$user/profile.jpg";

   # Otherwise show the default empty user from this url
   } else {
      $img_src = "https://chipinworld.com/assets1/images/about-image/no-image.jpg";
   }

   return $img_src;
}

# This function prints the navigation panel for the profile link, search bar, link
# to account settings and to logout
sub print_nav_bar {
   my $login_user = shift;

   # Starting with profile pic and profile with link to profile, and the news feed to
   # display all the posts from all the login user's mates
   $img_src = image_existence($login_user);
   print <<eof;
   <table position="relative" left="100px" >
   <tr>
      <td>
         <form action="" method="POST" class="light_text">
         <input type="hidden" name="login_user" value="$login_user" />
         <button type="submit" name="display_user" value="$login_user" class="button">
         <img src="$img_src" width=32 height=32>
         </button>
      </td>
      <td>
         <button type="submit" name="display_user" value="$login_user" class="button">
         <p class="light_text">Profile</p></button>
      </td>
      <td width="200px">
         <input type="hidden" name="display_user" value="$login_user" />
         <button type="submit" name="news_feed" value="true" class="button">
         <p class="light_text">News Feed</p></button>
         </form>
      </td>
eof

   # Printing out the search bar for users to search for other users or other users' posts
   print <<eof;
      <td width="380px">
         <form action="" method="POST" class="light_text">
         <input type="hidden" name="login_user" value="$login_user" />
         <input type="hidden" name="display_user" value="$login_user" />
         <p class="light_text"> Search: </p>
         <input type="radio" name="search" value="Mates" checked> Mates
         <input type="radio" name="search" value="Posts"> Posts
         <input type="text" name="keywords" id="sch"/>
         </form>
      </td>
eof


   # Printing the account settings tab and then the logout button without passing
   # hidden variable
   print <<eof;
      <td>
         <div align="right">
         <form action="" method="POST" class="light_text">
         <input type="hidden" name="login_user" value="$login_user" />
         <button type="submit" name="account_settings" value="$login_user" class="button">
         <p class="light_text">Account Settings</p></button>
         </form>

         <form action="" method="POST" class="light_text">
         <button type="submit" name="login_user" value="" class="button">
         <p class="light_text">Logout</p></button>
         </form>
         </div>
      </td>
   </tr>
   </table>
eof

}

# This function prints the list of results matching the keywords the login user typed in the
# search corresponding the the selected search for mates or posts within the privacy settings
sub print_search_results {
   my $login_user = shift;
   my $display_user = shift;

   # The keyword that the user entered in the search bar to search
   $keyword = param('keywords');
   $count = 0;       # counter for the number of items displayed

   # Parameters for pagination of results
   $items_per_pg = (param('search') eq "Mates") ? 10 : 5;
   param('page'=>1) if (!param('page'));   # the pagination of items to display
   $start = 1+ $items_per_pg*(param('page')-1);
   $end = $start+$items_per_pg-1;

   # If the user selected the search Mates checkbox, display the mates that match that keyword
   if (param('search') eq "Mates"){
      my @users = sort(glob("$users_dir/*"));
      foreach $user (@users){
         $user =~ s/$users_dir\///;
         next if (inactive($user) or $user eq $login_user);

         $full_name = find_in_file("$users_dir/$user/user.txt","full_name");

         $search_img = image_existence($user);
         if ($full_name =~ /$keyword/i){
            $count++;
            next unless ($count >= $start && $count <= $end);
            print <<eof
            <article>
            <form action="" method="POST">
            <input type="hidden" name="login_user" value="$login_user" />
            <button type="submit" name="display_user" value="$user" class="button">
            <input type="image" src="$search_img" width="32" height="32"></button>
            <button type="submit" name="display_user" value="$user" class="button">$full_name</button>
            </form>
            </article>
eof
         }
      }
   }

   # If the user selected the search Posts checkbox, display any posts
   if (param('search') eq "Posts") {
      my @users = sort(glob("$users_dir/*"));
      foreach $user_path (@users){

         # Checking the privacy settings of the poster
         my $user = $user_path =~ /z\d{7}/;
         next unless (privacy_permission($login_user,$user,"posts"));

         # Checking the posts if there are any matches
         @post_paths = sort(glob("$user_path/posts/*"));
         foreach $post_path (@post_paths){
            open F, "$post_path/post.txt" or die;
            $match = 0;
            foreach $line (<F>){
               $id_to_name = id_to_name($line);
               if ($line =~ /$keyword/i or $id_to_name =~ /$keyword/i){
                  $match = 1;
                  $count++;
                  last;
               }
            }
            print_post($post_path,$login_user) if ($match == 1 and $count >= $start && $count <= $end);
         }

      }
   }

   # Setting the item page intervals based on number of matching results counted
   if ($count > $items_per_pg){
      $num_pages = $count/$items_per_pg;
      $num_pages++ if ($count % $items_per_pg > 0);
      $news_feed = param('news_feed') || "";
      $search = param('search');
      print <<eof;
      <section style="background-color: #eeeeee">
      <form action="" method="POST" class="dark_text" align="right">
      <input type="hidden" name="login_user" value="$login_user" />
      <input type="hidden" name="news_feed" value="$news_feed" />
      <input type="hidden" name="search" value="$search" />
      <input type="hidden" name="keywords" value="$keyword" />
      <p class="dark_text"> Page:
eof
      for ($page = 1; $page <= $num_pages; $page++){
         $start = 1+ $items_per_pg*($page-1);
         $end = ($count < $start+$items_per_pg-1) ? $count : $start+$items_per_pg-1;
         if (param('page') != $page){
            print <<eof;
            <button type="submit" name="page" value="$page" class="button"> $start-$end </button>
eof
         } else {
            print <<eof;
            <body style="color: black"> <b>$start-$end</b> </div>
eof
         }
      }

      print <<eof;
      </form>
      </section>
eof
   }

}

# This function prints out the section for the user to view or change their account login details
# as well as to suspend or delete their account
sub print_account_settings {
   my $login_user = shift;
   my $display_user = shift;

   # Printing the section heading
   print <<eof;
   <section>
   <div align="center">
   <b> Account Settings </b>
   </div>
   </section>
   <section style="background-color: #eeeeee; padding-left: 50px">
   </p>
   <table position="relative" left="100px" >
   <form action="" method="POST" class="dark_text">
eof

   # Printing out the text fields of the user's details for them to edit
   my $username = find_in_file("$users_dir/$login_user/user.txt","zid");
   # Printing the password row of the table with the button to change their password
   my $password = find_in_file("$users_dir/$login_user/user.txt","password");
   # Showing their email
   my $email = find_in_file("$users_dir/$login_user/user.txt","email");

   my $new_pw = param('new_pw');
   # Checking if the user entered the right new password
   if (param('new_pw') and param('conf_pw') and !param('pw_changed')){
      if (param('new_pw') ne param('conf_pw')) {
         $password_prompt = "Passwords must match";
      } elsif ($new_pw =~ /[\/;`'\\<>= ]/){
         $password_prompt = "Password cannot contain any of (/;`'\\<>= )";
      }
   } else {
      $password_prompt = "";
   }

   # If the user clicked on 'change password', print two new boxes for them to change their password
   $password_change = "";
   if (param('change_password') and !param('pw_changed')){
      $password_change = <<eof;
      <tr>
      <td> New Password: </td>
      <td> <input type="password" name="new_pw" maxlength="16"/>  </td>
      </tr>
      <tr>
      <td> Confirm Password: </td>
      <td> <input type="password" name="conf_pw" maxlength="16"/>  </td>
      <td> <b style="color: red"> $password_prompt </b>
      </tr>
eof
   }

   # Setting the button for them to suspend or unsuspend their account
   switch (inactive($login_user)){
      case "suspended"  {$caption = "Ready to resume?"; $param_name = "unsuspend_account"; $button_name = "Unsuspend Account";}
      else             {$caption = "Take a break?";    $param_name = "suspend_account"; $button_name = "Suspend Account";}
   }

   # Printing the fields for the user to change their account details apart from the username or
   # to suspend or delete their account
   print <<eof;
   <tr>
      <td width="140px"> Username:    </td>
      <td width="170px"> <input type="text" disabled="disabled" value="$username"/>  </td>
      <td> <b style="color: red"> You cannot change your username </b>
   </tr>
   <tr>
      <td> Password:    </td>
      <td> <input type="password" disabled="disabled" value="$password"/>  </td>
      <input type="hidden" name="login_user" value="$login_user" />
      <input type="hidden" name="account_settings" value="$login_user" />
      <td> <button type="submit" name="change_password" value="$login_user" class="matelook_button">
            Change Password
           </button>
      $password_change
      </td>

   </tr>
   <tr>
      <td> Email:    </td>
      <td> <input type="test" disabled="disabled" value="$email"/>  </td>
      <td> <b style="color: red"> You cannot change your email </b>
      </td>
   </tr>
   <tr>
      <td> $caption    </td>
      <td>  </td>
      <td> <button type="submit" name="$param_name" value="$login_user" class="matelook_button">
            $button_name
           </button>
      </td>
   </tr>
   <tr>
      <td> Moving on?    </td>
      <td>   </td>
      <td> <button type="submit" name="delete_account" value="$login_user" class="matelook_button">
            Delete Account
           </button>
      </td>
   </tr>
eof

   # Completing the table
   print <<eof;
   </form>
   </table>
   </section>
eof
}

# This function prints the privacy section of the account settings for who they want to
# allow (me only, mates only or everyone) to view their profile elements
sub print_privacy_settings {
   my $login_user = shift;
   my $display_user = shift;

   # Printing the section heading
   print <<eof;
   <section>
   <div align="center">
   <b> Privacy </b>
   </div>
   </section>
   <form action="" method="POST" class="dark_text">
   <input type="hidden" name="login_user" value="$login_user" />
   <input type="hidden" name="account_settings" value="$login_user" />
   <section style="background-color: #eeeeee; padding-left: 50px">
   <table position="relative" left="100px" >
   <tr>
   Who can see your details? </p>
   </tr>
eof

   # Printing out the text fields of the user's details for them to edit
   foreach $title ("Posts","Mate List","Profile Text","Program","Home Suburb",
                   "Email","Birthday","Home Latitude","Home Longitude","Courses"){

      my $deet = lc($title);
      $deet =~ s/ /_/;
      my $set = get_privacy_setting($login_user,$deet);

      # Determining which settings to show checked based on the privacy setting or default
      chomp $set;
      switch ($set){
         case "everyone"        {$check1 = "checked"; $check2 = "";       $check3 = ""}
         case "mates"           {$check1 = "";       $check2 = "checked"; $check3 = ""}
         case "me"              {$check1 = "";       $check2 = "";        $check3 = "checked"}
      }

      # Printing the radio buttons for each detail
      print <<eof;
      <tr>
         <td width="150">
            <fieldset id="privacy_$deet">
            <u> $title:  </u>
         </td>
         <td width="120">
            <input type="radio" name="privacy_$deet" value="everyone" $check1> Everyone
         </td>
         <td width="120">
            <input type="radio" name="privacy_$deet" value="mates" $check2> Mates Only
         </td>
         <td width="120">
            <input type="radio" name="privacy_$deet" value="me" $check3> Me Only
            </fieldset>
         </td>
      </tr>
eof
   }

   # Ending the privacy section
   print <<eof;
   </table>
   <div align="right">
   <button type="submit" name="save_privacy" value="$login_user" class="matelook_button">Save</button>
   </form>
   </div>
   </section>
eof

}

# This function prints the relation of the displayed user to the login user above the displayed
# user's profile picture. It states if they are mates, or having a button for them to send a mate request,
# otherwise for the login user's page, shows the pending mate requests
sub print_mate_status {
   my $display_user = shift;
   my $login_user = shift;

   # If the login user is viewing a different user, display if they are a mate, or
   # the option to add them, or whether their request has been sent
   if ($display_user ne $login_user){
      # if they are already mates
      if (are_mates($login_user,$display_user)){
         print <<eof;
         <div align="center">
         <b align="center"> You are mates </b>
         </div>
eof
      # if they are not mates, display if request has been sent or button to request mate
      } else {

         $their_mate_requests = find_in_file("$users_dir/$display_user/user.txt","mate_requests");
         $my_mate_requests = find_in_file("$users_dir/$login_user/user.txt","mate_requests");

         # if they have received my request
         if ($their_mate_requests =~ /$login_user/) {
            print <<eof;
            <div align="center">
            <b> Mate Request Sent </b>
            </div>
eof
         # if I have a request from the diplayed user, display confirm button
         } elsif ($my_mate_requests =~ /$display_user/){
            $first_name = find_in_file("$users_dir/$display_user/user.txt","full_name");
            $first_name =~ s/\s.*$//;;

            print <<eof;
            <div align="center">
            <form action="" method="POST">
            <b> $first_name has sent you a mate request: </b>
            <input type="hidden" name="login_user" value="$login_user" />
            <input type="hidden" name="display_user" value="$display_user" />
            <button type="submit" name="confirm_mate" value="$display_user" class="matelook_button">
            Confirm Mate</button>
            </form>
            </div>
            </br>
eof
         # if the request hasn't been sent, show the button to send it
         } else {

            print <<eof;
            <div align="center">
            <form action="" method="POST" class="light_text">
            <input type="hidden" name="login_user" value="$login_user" />
            <input type="hidden" name="display_user" value="$display_user" />
            <button type="submit" name="mate_request" value="$display_user" class="matelook_button">
            <p>Send Mate Request</p> </button>
            </form>
            </div>
            </br>
eof
         }
      }

   # If the login user is viewing their own page, then notify them of mate requests
   } else {
      $mate_requests = find_in_file("$users_dir/$login_user/user.txt","mate_requests");
      @mates_to_add = $mate_requests =~ /z\d{7}/g;
      $num_mates = @mates_to_add;

      print <<eof if (@mates_to_add > 0);
      <div align="center">
      <b > You have $num_mates mate request(s) </b>
      </div>
eof
      # Print each mate's request
      foreach $mate (@mates_to_add){
         $full_name = find_in_file("$users_dir/$mate/user.txt","full_name");
         $search_img = image_existence($mate);

         print <<eof if (!inactive($mate));
         <form action="" method="POST">
         <input type="hidden" name="login_user" value="$login_user" />
         <button type="submit" name="display_user" value="$mate" class="button">
         <input type="image" src="$search_img" width="32" height="32"></button>
         <button type="submit" name="display_user" value="$mate" class="button_small">$full_name</button>
         <button type="submit" name="confirm_mate" value="$mate" class="matelook_button">Confirm Mate</button>
         </form>
         </br>
eof

      }

   }
}

# This function prints out the user details for the input display user and also
# the private details if it's the login user's page
sub print_user_details {
   my $display_user = shift;
   my $login_user = shift;

   my $details_filename = "$users_dir/$display_user/user.txt";
   open F, "$details_filename" or die "can not open $details_filename: $!";
   @user_details = <F>;
   close F;
   foreach $detail (@user_details) {
      $detail =~ /(.*)=(.*)/;
      $deets{$1} = $2;
   }

   # printing name of the displayed user and the heading of user details with option to edit
   if (defined($deets{full_name})){
      $full_name = $deets{full_name};
   } else {
      $full_name = "Matelook User";
   }

   # Variable for profile text div if the user chose to add profile text
   if (defined $deets{profile_text} and privacy_permission($login_user,$display_user,"profile_text")){
      $profile_text = <<eof;
      <div class="matelook_user_details" align="center">
      <i>$deets{profile_text}</i>
      </div>
eof
   } else {
      $profile_text = "";
   }

   # Printing option for login user to edit their details
   $option = ($display_user ne $login_user) ? "" : <<eof;
   (<input type="hidden" name="login_user" value="$login_user" />
   <button type="submit" name="change_user_details" value="$login_user" class="button_small">edit</button>)
eof

   print <<eof;
   <h1 class="center">$full_name</h1>
   <form action="" method="POST">
   $profile_text
eof

   if (privacy_permission($login_user,$display_user,"user_details")){
   print <<eof;
   <p class="center"> User Details
   $option
   </p>
   </form>
   <div class="matelook_user_details">
eof

   # translating the courses to only the course codes
   @courses = $deets{courses} =~ /\w{4}\d{4}/g if (defined $deets{courses});
   my $course_string = join ', ', @courses;
   $deets{courses} = $course_string;

   foreach $title ("Program","Home Suburb","Email","Birthday",
                              "Home Latitude","Home Longitude","Courses"){
      my $param = lc($title);
      $param =~ s/ /_/;
      my $param_value = $deets{$param} || "";
      print <<eof if ($param_value and privacy_permission($login_user,$display_user,$param));
      <b>$title: </b> $param_value </br>
eof

   }

   # Printing out list of mates as links
   print <<eof;
   </div>
eof
   }
}

# This function prints the section for the user to upload or delete a profile or background picture
sub print_change_user_pictures {
   my $login_user = shift;
   my $display_user = shift;

   # Printing the section heading
   print <<eof;
   <section>
   <div align="center">
   <b> Change Profile Pictures </b>
   </div>
   </section>
   <section style="background-color: #eeeeee; padding-left: 50px">
   <form action="" method="POST" enctype="multipart/form-data">
   </p>
eof
   # Printing the options to upload or change the login user's profile pic or background pic
   foreach $pic ("Profile", "Background"){
      my $param = lc($pic);
      my $file_param = "$param"."_pic";

      # Setting the option to delete the uploaded picture if there was one
      my $delete_option = !(-e "$users_dir/$login_user/$param.jpg") ? "" : <<eof;
      <button type="submit" name="remove_$param" value="$login_user" class="matelook_button">Remove</button>
eof
      # Printing the upload options
      print <<eof;
      Change $pic Picture: <input type="file" name="$file_param" accept"image/*">
      <button type="submit" name="change_$param" value="$login_user" class="matelook_button">Upload</button>
      $delete_option
      </p>
eof
   }

   # Ending the user picture section
   print <<eof;
   <div align="right">
   <input type="hidden" name="login_user" value="$login_user"/>
   <input type="hidden" name="display_user" value="$login_user" />
   <input type="hidden" name="change_user_details" value="$login_user"/>
   </div>
   </section>
eof
}

# This function prints the section for the user to change any of their user details which also
# updates their user.txt file
sub print_change_user_details {
   my $login_user = shift;
   my $display_user = shift;

   # Printing the section heading
   print <<eof;
   <section>
   <div align="center">
   <b> Change User Details </b>
   </div>
   </section>
   <section style="background-color: #eeeeee; padding-left: 50px">
   </p>
eof

   # Starting a table to display the text boxes to edit the user's details
   print <<eof;
   <table position="relative" left="100px" >
   </p>
eof

   # Printing out the text fields of the user's details for them to edit
   foreach $title ("Profile Text","Full Name","Program","Home Suburb",
                                                   "Birthday","Home Latitude","Home Longitude"){
      $deet = lc($title);
      $deet =~ s/ /_/;
      $value = find_in_file("$users_dir/$login_user/user.txt",$deet);
      print <<eof;
      <tr>
         <td> $title:    </td>
         <td> <input type="text" name="$deet" value="$value" style="width: 300px" maxlength="100"/> </td>
      </tr>
eof
   }

   # Setting the prompt to show user how to add a courser
   $prompt = !(param('add_course') and param('add_course') eq "invalid") ? "" : <<eof;
   <tr><td></td><td>
   <p style="color: red"> Enter course like '2016' 'S1' 'ENGG1000' </p></td>
   </tr>
eof
   # Printing out the year, sem and course code for adding courses
   print <<eof;
   <tr>
      <td> Add Courses:    </td>
      <td>
         Year:<input type="text" name="year" style="width: 40px" maxlength="4"/>
         Sem:<input type="text" name="semester" style="width: 20px" maxlength="1"/>
         Course:<input type="text" name="course" style="width: 80px" maxlength="8"/>
         <button type="submit" name="add_course" value="$login_user" class="matelook_button">Add</button>
      </td>
   </tr>
   $prompt
eof

   # Listing the current courses added with an option to delete certain ones
   my $course_string  = find_in_file("$users_dir/$login_user/user.txt","courses");
   @courses = $course_string =~ /\d{4} \w\d \w{4}\d{4}/g;
   foreach $course (@courses){
      print <<eof;
      <tr>
         <td></td>
         <td>
            <b> $course </b>
            <button type="submit" name="delete_course" value="$course" class="button_small">delete</button>
         </td>
      </tr>
eof
   }

   # Completing the table
   print <<eof;
   </table>
   <div align="right">
   <button type="submit" name="save_user_details" value="$login_user" class="matelook_button">Save</button>
   <input type="hidden" name="login_user" value="$login_user"/>
   <input type="hidden" name="display_user" value="$login_user" />
   <input type="hidden" name="change_user_details" value="$login_user"/>
   </div>
   </form>
   </section>
eof

}

# This function prints out the list of the mates of the displayed users if the login user
# has the privacy permissions to view that user's mates
sub print_user_mates {
   my $display_user = shift;
   my $login_user = shift;

   # Don't display anything if the user doesn't have the permissions
   return if (!privacy_permission($login_user,$display_user,"mate_list"));

   # Defining the HTML for the (manage mates) link to appear only if the login user is viewing their own page
   $option = ($display_user ne $login_user) ? "" : <<eof;
   (<input type="hidden" name="login_user" value="$login_user" />
   <button type="submit" name="manage_mates" value="$login_user" class="button_small">manage mates</button>)
eof

   # Printing out the title and start of the div
   print <<eof;
   <form action="" method="POST">
   <p class="center"> Mates
   $option
   </p>
   </form>
   <div class="matelook_mates">
eof
   # Gathering the display user's mates in an array to print as a list
   $mates_string = find_in_file("$users_dir/$display_user/user.txt","mates");
   @mates = $mates_string =~ /z\d{7}/g;
   foreach $mate (@mates){
      my ($button_on, $button_off) = active_user_link($login_user,$mate);

      $mate_name = find_in_file("$users_dir/$mate/user.txt","full_name");
      $user_img = image_existence($mate);
      print <<eof;
      <div>
      <form action="" method="POST">
      <input type="hidden" name="login_user" value="$login_user" />
      $button_on <img src="$user_img" width="64" height="64"> $button_off
      $button_on $mate_name $button_off
      </form>
      </div> </br>
eof
   }

   # Ending the mate list div
   print <<eof;
   </div>
eof
}

# This function prints out the list of the login user's mates with the option to
# delete them from the mate list
sub print_manage_mates {
   my $login_user = shift;
   my $display_user = shift;

   # Printing the section heading
   print <<eof;
   <section>
   <div align="center">
   <b> My Mates </b>
   <div>
   </section>
eof
   # Gathering the string of mates of the login user into an array
   $mates_string = find_in_file("$users_dir/$login_user/user.txt","mates");
   @mates = $mates_string =~ /z\d{7}/g;

   # Printing out each mate's name and link to delete the mate from the user's mate list
   foreach $mate (@mates){
      $mate_name = find_in_file("$users_dir/$mate/user.txt","full_name");
      $user_img = image_existence($mate);

      # Inactive mates are displayed without a link
      my ($button_on, $button_off) = active_user_link($login_user,$mate);

      print <<eof;
      <article>
      <form action="" method="POST">
      <input type="hidden" name="login_user" value="$login_user"  />
      <input type="hidden" name="display_user" value="$login_user" />
      <input type="hidden" name="manage_mates" value="$login_user"/>
      $button_on <img src="$user_img" width="32" height="32"> $button_off
      $button_on $mate_name $button_off
      <button type="submit" name="delete_mate" value="$mate" class="button"> delete</button>
      </form>
      </article>
eof
   }
}

# This function prints out the ranked list of suggested mates under the manage_mates section
# There are 3 ways to rank potential mates by distance, common courses or mutual mates
sub print_suggest_mates {
   my $login_user = shift;
   my $display_user = shift;

   # Printing the header for the suggested mates with radio buttons for the user to select
   # how they want to rank the suggested mates
   print <<eof;
   </p>
   <section>
   <div align="center">
   <form action="" method="POST">
      <input type="hidden" name="login_user" value="$login_user" />
      <b> Suggested Mates based on: </b>
      <input type="radio" name="suggest" value="Distance" checked>   Distance
      <input type="radio" name="suggest" value="Common_Courses">     Common Courses
      <input type="radio" name="suggest" value="Mutual_Mates">       Mutual Mates
      <button type="submit" name="manage_mates" value="$login_user" class="matelook_button"> Suggest
      </button>
   </form>
   <div>
   </section>
eof
   # Getting an array called non_mates of users that aren't mates with the login user and excluding
   # the users with their accounts suspended
   my @users = sort(glob("$users_dir/*"));
   my $mates_string = find_in_file("$users_dir/$login_user/user.txt","mates");
   foreach $user_dir (@users){
      $user_dir =~ /(z\d{7})/;
      my $user = $1;

      # If the user's account is not suspended, or if the login user's account is not suspended
      push @non_mates, $user if (!are_mates($login_user,$user) and $login_user ne $user and !inactive($user));
   }

   # Sorting the non_mates by common courses, mutual mates or distance away based on how the login_user chose
   # to rank the suggestions

   # For common courses, rank by the highest number of courses in common
   if (param('suggest') and param('suggest') eq "Common_Courses"){
      @sorted_suggestions = reverse sort {common_items($login_user,$a,"courses") <=> common_items($login_user,$b,"courses")} @non_mates;

   # For mutual mates, rank by highest number of mates in common
   } elsif (param('suggest') and param('suggest') eq "Mutual_Mates"){
      @sorted_suggestions = reverse sort {common_items($login_user,$a,"mates") <=> common_items($login_user,$b,"mates")} @non_mates;

   # For distance, rank with the smallest distance between the users based on the home lat and long
   } else {
      param('suggest'=>"Distance");
      @sorted_suggestions = sort {dist_from_mate($login_user,$a) <=> dist_from_mate($login_user,$b)} @non_mates;
   }

   # Counting the number of significant matches to display to the login user where matches with zero common
   # courses or mates are redundant and more than 100km away is not feasible
   $num_significant = 0;
   foreach $element (@sorted_suggestions) {
      switch (param('suggest')){
         case "Common_Courses" {$num_significant++ if (num_common_items($login_user,$element,"courses") > 0)}
         case "Mutual_Mates"   {$num_significant++ if (num_common_items($login_user,$element,"mates") > 0)}
         else                  {$num_significant++ if (dist_from_mate($login_user,$element) < 500)}
      }
   }

   # Setting the limit of results per page
   $items_per_pg = 10;
   # Checking for need to separate to pages
   if ($num_significant > $items_per_pg){
      # Declaring pagination is required
      $pagination = 1;

      # Defining the number of pages needed to separate the posts and adding 1 if the
      # number of posts isn't completely divisible into the number of items per page
      $num_pages = $num_significant/$items_per_pg;
      $num_pages++ if ($num_significant % $items_per_pg > 0);

      # Setting the default current page to be the first lot
      param('page'=>1) if (!param('page'));

      # Setting the index of the post array for which to print the posts for that page
      $start = 1+ $items_per_pg*(param('page')-1);
      $end = ($num_significant < $start+$items_per_pg-1) ? $num_significant : $start+$items_per_pg-1;

   # Otherwise, the indices would just be the boundaries of the array
   } else {
      $start = 1;
      $end = $num_significant;
   }

   # Print out the ranked list of suggestions if they are significant
   foreach (my $i = $start; $i <= $end; $i++){
      $mate = $sorted_suggestions[$i-1];

      # Standard mate details
      $mate_name = find_in_file("$users_dir/$mate/user.txt","full_name");
      $user_img = image_existence($mate);
      my $item_list = "";

      # Defining a caption to describe how the mate is a good suggestion

      # For common courses, the most common courses are first,
      if (param('suggest') and param('suggest') eq "Common_Courses"){
         $num_common_courses = num_common_items($login_user,$mate,"courses");
         $caption = "has done $num_common_courses common subjects with you: ";

         # and also displays the courses
         @common_courses = common_items($login_user,$mate,"courses");
         next if (@common_courses < 1);
         foreach $course (@common_courses){
            $course =~ /(\w{4}\d{4})/;
            $item_list.= "$1  ";
         }

      # For mutual friends, the most mutuals friends first,
      } elsif (param('suggest') and param('suggest') eq "Mutual_Mates"){
         $num_mutuals = num_common_items($login_user,$mate,"mates");
         $caption = "has $num_mutuals mutual mates with you";

         # and dispaying the thumbnails of the mutuals
         @mutual_mates = common_items($login_user,$mate,"mates");
         next if (@mutual_mates < 1);
         foreach $mutual (@mutual_mates){
            $mutual_img = image_existence($mutual);
            $mutual_name = find_in_file("$users_dir/$login_user/user.txt","full_name");
            $item_list.= <<eof;
            <img src="$mutual_img" width="32" height="32" alt="$mutual_name"></button>
eof
         }

      # For distance away, start with the closest, and display how far they live
      } else {
         $dist_away = dist_from_mate($login_user,$mate);
         $dist_away =~ /(\d+\.\d)/;

         $caption = ($1) ? "lives $1 kms from you" : "has not specified location";
      }

      # The form to click to view the mate's profile
      print <<eof;
      <article>
      <form action="" method="POST">
      <input type="hidden" name="login_user" value="$login_user"  />
      <button type="submit" name="display_user" value="$mate" class="button">
      <img src="$user_img" width="32" height="32"></button>
      <button type="submit" name="display_user" value="$mate" class="button">$mate_name</button>
      $caption
      <b> $item_list </b>
      </form>
      </article>
eof
      }

   # Printing out the item interval links at the bottom of the displayed items
   if ($pagination){
      $suggest = param('suggest') || "Distance";

      # The initial section for holding the page interval links
      print <<eof;
      <section style="background-color: #eeeeee">
      <form action="" method="POST" class="dark_text" align="right">
      <input type="hidden" name="login_user" value="$login_user" />
      <input type="hidden" name="manage_mates" value="$login_user"/>
      <input type="hidden" name="suggest" value="$suggest"/>
      <p class="dark_text"> Page:
eof
      # Printing each interval for each page number
      for ($page = 1; $page <= $num_pages; $page++){
         $start = 1+ $items_per_pg*($page-1);
         $end = ($num_significant < $start+$items_per_pg-1) ? $num_significant : $start+$items_per_pg-1;

         # Printing links only for the pages other than the current one
         if (param('page') != $page){
            print <<eof;
            <button type="submit" name="page" value="$page" class="button"> $start-$end </button>
eof
         # Otherwise, just print it solid black
         } else {
            print <<eof;
            <body style="color: black"> <b>$start-$end</b> </div>
eof
         }
      }

      # Ending the suggested mates section
      print <<eof;
      </form>
      </section>
eof
   }

}

# This function prints out all the posts on the user's page depending on the privacy permissions
# between the poster and the login user and including page section links
sub print_post_feed {
   my $login_user = shift;
   my $display_user = shift;
   my $news_feed = param('news_feed') || "";

   # Printing text box form at the top for users to make posts
   print <<eof if ($display_user eq $login_user);
   <section>
   <form action="" method="POST" class="dark_text">
   <input type="hidden" name="login_user" value="$login_user" />
   <input type="hidden" name="news_feed" value="$news_feed" />
   <p class="dark_text"> Make Post: </p> <input type="text" name="post" style="width: 480px"/>
   </form>
   </section>
eof
   # Initializing array of post paths to print out
   my @user_posts = ();

   # Adding the display user's posts to the list if the permissions of privacy allow it
   if (privacy_permission($login_user,$display_user,"posts") and !(inactive($login_user) && param('news_feed'))){
      @user_posts = glob("$users_dir/$display_user/posts/*");
   }

   # Adding the privacy permitted mate posts to the news feed if 'news_feed' view was selected
   if (param('news_feed') and !inactive($login_user)){
      foreach $mate (@mates) {
         next if (!privacy_permission($login_user,$display_user,"posts") and !inactive($mate));
         my @mates_posts = glob("$users_dir/$mate/posts/*");
         push @user_posts, @mates_posts;
      }
   }

   # Static variable for number of posts to have on each page section
   my $items_per_pg = 5;

   # Sorting the posts by absolute date using the 'get_date' function starting with most recent
   @sorted_user_posts = sort {get_date("$a/post.txt") <=> get_date("$b/post.txt")} @user_posts;
   @sorted_user_posts = reverse @sorted_user_posts;

   # Checking for need to separate to pages
   if (@sorted_user_posts > $items_per_pg){
      # Declaring pagination is required
      $pagination = 1;

      # Defining the number of pages needed to separate the posts and adding 1 if the
      # number of posts isn't completely divisible into the number of items per page
      $num_pages = @sorted_user_posts/$items_per_pg;
      $num_pages++ if (@sorted_user_posts % $items_per_pg > 0);

      # Setting the default current page to be the first lot
      param('page'=>1) if (!param('page'));

      # Setting the index of the post array for which to print the posts for that page
      $start = 1+ $items_per_pg*(param('page')-1);
      $end = (@sorted_user_posts < $start+$items_per_pg-1) ? @sorted_user_posts : $start+$items_per_pg-1;

   # Otherwise, the indices would just be the boundaries of the array
   } else {
      $start = 1;
      $end = @sorted_user_posts;
   }

   # Printing out each post section from the array
   foreach ($i = $start; $i <= $end; $i++){
      print_post($sorted_user_posts[$i-1],$login_user,$display_user);
   }

   # Printing out the item interval links at the bottom of the displayed items if pagination was required
   if ($pagination){
      $news_feed = param('news_feed') || "";

      # The initial section for holding the page interval links
      print <<eof;
      <section style="background-color: #eeeeee">
      <form action="" method="POST" class="dark_text" align="right">
      <input type="hidden" name="login_user" value="$login_user" />
      <input type="hidden" name="news_feed" value="$news_feed" />
      <p class="dark_text"> Page:
eof
      # Printing each interval for each page number
      for ($page = 1; $page <= $num_pages; $page++){
         my $start = 1+ $items_per_pg*($page-1);
         my $end = (@sorted_user_posts < $start+$items_per_pg-1) ? @sorted_user_posts : $start+$items_per_pg-1;

         # Printing links only for the pages other than the current one
         if (param('page') != $page){
            print <<eof;
            <button type="submit" name="page" value="$page" class="button"> $start-$end </button>
eof
         # Otherwise, just print it solid black
         } else {
            print <<eof;
            <body style="color: black"> <b>$start-$end</b> </div>
eof
         }
      }

      # Ending the post page section
      print <<eof;
      </form>
      </section>
eof
   }

}

# This function prints out a post section containing the main post and the comments
sub print_post {
   my $post_path = shift;
   my $login_user = shift || param('login_user');
   my $display_user = shift || $login_user;

   # Each post has its own section div
   print "<section>\n";

   # Getting the details of 'from', 'time' and 'message' of the comment
   open $FILE, "$post_path/post.txt" or die "can't open $user: $!";
   my @post = <$FILE>;
   foreach $detail (@post) {
      $detail =~ /(.*)=(.*)/;
      $post_deets{$1} = $2;
   }
   close $FILE;

   # Setting up post frame
   print <<eof;
   <post>
   <div class="tst1">
eof
   # Profile pic thumbnail
   $post_id = $post_deets{from};
   $post_name = id_to_name($post_id);
   print_display_pic($post_id,32);

   # Formatting the message
   $message = id_to_name($post_deets{message});
   $message =~ s/\\n/<\/br>/g;
   $post_time = print_time($post_deets{time});

   # setting the link to the user who made their post if both the login user
   # and the posting user are not suspended
   my ($button_on, $button_off) = active_user_link($login_user,$post_id);

   # Printing the post
   print <<eof;
   </div>
   <form action="" method="POST">
   <input type="hidden" name="login_user" value="$login_user" />
   $button_on $post_name: $button_off $message </br>
   </form>
   <div style="color:grey"> $post_time </div>
   </post>
eof

   # Printing delete button for login user to the delete their own post
   print <<eof if ($post_id eq $login_user);
   <form action="" method="POST">
   <input type="hidden" name="login_user" value="$login_user" />
   <input type="hidden" name="display_user" value="$display_user" />
   <button type="submit" name="delete_post" value="$post_path" class="button_small">Delete</button>
   </form>
eof

   # Calling the print_comment function for each comment path to print the comments for that post
   my @comments = glob("$post_path/comments/*");
   @sorted_comments = sort {get_date("$a/comment.txt") <=> get_date("$b/comment.txt")} @comments;
   foreach $comment_path (@sorted_comments){

      print "<article>";
      print_comment($comment_path,$login_user,$display_user);
      print "</article>\n";

   }

   # Printing textbox for user to leave replies only if the login user is mates with
   # the displayed user
   print <<eof if (are_mates($login_user,$display_user) || $display_user eq $login_user);
   <form action="" method="POST" class="dark_text">
   <input type="hidden" name="login_user" value="$login_user" />
   <input type="hidden" name="display_user" value="$display_user" />
   <input type="hidden" name="comment_path" value="$post_path" />
   <p class="dark_text"> Post Comment: </p> <input type="text" name="comment" style="width: 300px"/>
   </form>
eof

   print "</section>\n";
}

# This function prints a formatted comment for a given comment_path of a post
sub print_comment {
   my $comment_path = shift;
   my $login_user = shift;
   my $display_user = shift;

   # Getting the details of 'from', 'time' and 'message' of the comment
   open $FILE, "$comment_path/comment.txt" or die "can't open $user: $!";
   my @comment= <$FILE>;
   foreach $detail (@comment) {
      $detail =~ /(.*)=(.*)/;
      $comment_deets{$1} = $2;
   }
   close $FILE;

   # Setting the thumbnail source and name of the user who made the comment
   $from_id = $comment_deets{from};
   $from_name = id_to_name($from_id);
   $thumbnail_src = image_existence($from_id);
   $message = ($tag_ids) ? id_to_link($comment_deets{message}) : id_to_name($comment_deets{message});
   $message = id_to_name($comment_deets{message}) if (inactive($login_user));
   $message =~ s/\\n/<\/br>/g;
   $comment_time = print_time($comment_deets{time});

   # determining whether to allow links to that mate's comment depending on whether
   # their account or the login user's account is suspended
   my ($button_on, $button_off) = active_user_link($login_user,$from_id);

   # Printing the HTML body of the comment
   print <<eof;
   <div.tst1 display="inline">
   <form action="" method="POST">
   <input type="hidden" name="login_user" value="$login_user" />
   $button_on <input type="image" src="$thumbnail_src" width="32" height="32"> $button_off
   $button_on $from_name:     $button_off
   </form>
   $message
   </br>
   <div style="color:grey"> $comment_time </div>
   </div>
eof

   # Printing delete button for comment
   print <<eof if ($from_id eq $login_user or $post_id eq $login_user);
   <form action="" method="POST">
   <input type="hidden" name="login_user" value="$login_user" />
   <input type="hidden" name="display_user" value="$display_user" />
   <button type="submit" name="delete_comment" value="$comment_path" class="button_small">Delete</button>
   </form>
eof
}

# This function creates the file to hold the information for a post and adds the information
# along with the properly formatted time to it
sub make_post_file {
   my $path = shift;
   my $message = shift;
   my $login_user = shift;

   # Adding the from and message parameters to the post or comment file
   open F, '>'."$path" or die;
   print F "from=$login_user\n";
   print F "message=$message\n";

   # Calling the perl time library function to print the date in the required format
   $datestring = strftime "%FT%X+0000", localtime;
   print F "time=$datestring\n";
   close F;
}

# This function returns the value of a parameter for a particular user by looking in the
# path file for it
sub find_in_file {
   my $path = shift;
   my $param = shift;
   my $value = "";

   # Searching user.txt for the parameter if the path exists
   if (-e $path){
      open my $FILE, "$path" or die "can't open $path: $!";
      foreach $line (<$FILE>){
         if ($line =~ /$param=/){
            $value = $line;
            $value =~ s/[^=]*=//;   # Only getting the value of the parameter
            last;
         }
      }
      close $FILE;
   }

   return $value;
}

# This function returns the date string as a number which will be used to order the users'
# posts by the most significant date element to the least
sub get_date {
   my $comment_path = shift;

   # converting the string into an integer to represent the absolute point in time
   $time_string = find_in_file($comment_path,time);
   $time_num = $time_string =~ /\d/g;

   return int($time_num);
}

# This function translates the comment date format to a readable format for displaying on the user page
sub print_time {
   my $time_string = shift;

   @months = ("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec");

   # The format used in user.txt
   $time_string =~ /(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d:\d\d:\d\d)/;
   $year = $1;
   $month = $2;
   $day = $3;
   $time = $4;

   return "$day $months[$month-1] $year at $time";
}

# This function deletes a specified item (a mate or a course) from the login user's user.txt file
sub add_items {
   my $item_to_add = $_[2];
   my $param = $_[1];
   my $login_user = $_[0];

   # Getting the current string of items
   $old_items = find_in_file("$users_dir/$login_user/user.txt","$param");

   # checking that the user's request isn't already in there
   unless ($old_items =~ /$item_to_add/){

      # Restructuring the string of items by adding them to an array
      if ($param =~ /mate/){
         @new_items = $old_items =~ /z\d{7}/g;
      } elsif ($param =~ /courses/) {
         @new_items = $old_items =~ /\d{4} S\d \w{4}\d{4}/g;
      }

      # Adding the new item and then joining them together as a new string
      push @new_items, $item_to_add;
      $new_items_string = join ', ', @new_items;

      # Modifying the current parameter string if it exists otherwise creating the parameter entry
      if (!modify_file_param("$users_dir/$login_user/user.txt","$param","[$new_items_string]\n")){
         add_param_to_file("$users_dir/$login_user/user.txt","$param","[$new_items_string]\n");
      }
   }
}

# This function deletes a specified item (a mate or a course) from the login user's user.txt file
sub delete_items {
   my $item_to_delete = $_[2];
   my $param = $_[1];
   my $login_user = $_[0];

   # Getting the current string of items and deleting the matched item to delete
   $old_items = find_in_file("$users_dir/$login_user/user.txt","$param");
   $old_items =~ s/$item_to_delete//;

   # Restructuring the string of items by adding them to an array
   if ($param =~ /mate/){
      @new_items = $old_items =~ /z\d{7}/g;
   } elsif ($param =~ /courses/) {
      @new_items = $old_items =~ /\d{4} S\d \w{4}\d{4}/g;
   }

   # And joining the items with the proper separator to maintain the format in user.txt
   $new_items_string = join ', ', @new_items;

   # Replacing the ond string with the new one
   modify_file_param("$users_dir/$login_user/user.txt","$param","[$new_items_string]\n");

}

# This function replaces an 'old line' in an input path to a file with a 'new line' and skips
# any blank lines in between. It returns whether the old line was found and replaced
sub modify_file_param {
   my $path = shift;
   my $param = shift;
   my $new_value = shift;

   # Array for temporarily holding the file contents while they are replaced
   @new_contents = ();
   $add_success = 0;

   # adding original lines to the new contents array until it gets to 'old_line'
   # then replace with the 'new_line'
   open my $FILE, "<"."$path" or die "can't open $path";
   foreach $line (<$FILE>){
      if ($line =~ /^$param=/) {
         push @new_contents, "$param=$new_value\n";
         $add_success = 1;
      } else {
         push @new_contents, $line unless ($line =~ /^$/);
      }
   }
   close $FILE;

   # reopening the file to write the array contents over the old contents
   open my $NEW, ">"."$path" or die "can't open $path";
   foreach $line (@new_contents){
      print $NEW $line;
   }
   close $NEW;

   return $add_success;
   # source: http://stackoverflow.com/questions/2278527/how-do-i-replace-lines-in-the-middle-of-a-file-with-perl
}

# This function appends an input line to the end of a file if the file path exists
sub add_param_to_file {
   my $path = shift;
   my $param = shift;
   my $line_to_add = shift;

   $add_success = 0;

   if (!find_in_file("$path", $param)){
      open my $FILE, ">>"."$path" or die "can't open $path";
      print $FILE "\n$param=$line_to_add";

      $add_success = 1 if (find_in_file("$path", $param));
   }

}

# This function calculates the distance between two mates and returns the number of kilometers
# in a straight line from the two locations based on an algorithm found online
sub dist_from_mate {
   my $from_mate = shift;
   my $to_mate = shift;

   # Defining the fixed parameters
   $earth_radius = 6371; # km
   $pi = 3.14159265;
   $deg_to_rad = $pi/180;

   # Finding the coordinates of the from mate
   $from_lat = find_in_file("$users_dir/$from_mate/user.txt","home_latitude");
   $from_long = find_in_file("$users_dir/$from_mate/user.txt","home_longitude");

   # Finding the coordinates of the to mate
   $to_lat = find_in_file("$users_dir/$to_mate/user.txt","home_latitude");
   $to_long = find_in_file("$users_dir/$to_mate/user.txt","home_longitude");

   # The algorithm will only be valid if all the required coordinates exist in the user's file
   if ($from_lat && $from_long && $to_lat && $to_long){

      # Finding the lat and long difference in radians
      $d_lat = ($to_lat-$from_lat) * $deg_to_rad;
      $d_long = ($to_long-$from_long) * $deg_to_rad;

      # calculating the arc length between the two points
      my $a = (sin($d_lat/2))**2 + cos($to_lat * $deg_to_rad)*cos($from_lat * $deg_to_rad)*(sin($d_long/2))**2;
      my $c = 2*atan2(sqrt($a),sqrt(1-$a));

      $d = $c * $earth_radius;

   # If one coordinate was not found, return a really large distance to ignore
   } else {
      $d = 999999;
   }

   return $d;
   # source: http://andrew.hedges.name/experiments/haversine/
}

# This function returns an array of the common items (param = courses or mates) of two input users
# It uses a hash to count the number of occurences of the item in the two user's data and counts
# duplicate items as matches which are added to an array of common items to return
sub common_items {
   my $mate_1 = shift;
   my $mate_2 = shift;
   my $param = shift;

   # An array to be returned that holds all the common items between the two mates
   my @commons = ();
   my %item_count = (); # The hash to count the frequency

   # Add the items to the hash for each user's item list
   foreach $mate ($mate_1,$mate_2){

      # Finding the string of the items
      my $item_string = find_in_file("$users_dir/$mate/user.txt","$param");

      # Determining how to split the string into individual items depending on what
      # item parameter was passed in and the format of the user.txt items
      if ($param =~ /mates/){
         @items = $item_string =~ /z\d{7}/g;
      } elsif ($param =~ /courses/) {
         @items = $item_string =~ /\d{4} S\d \w{4}\d{4}/g;
      }

      # Adding each item to the hash
      foreach $item (@items){
         if (defined $item_count{$item}){
            $item_count{$item}++;
         } else {
            $item_count{$item} = 1;
         }
      }
   }

   # Grabbing the duplicate items
   foreach $item (keys %item_count){
      push @commons, $item if ($item_count{$item} > 1);
   }

   return @commons;
}

# This function is the scalar version of 'common_items' where it returns the number of elements
# of common items added to the returned array from 'common_items' for sorting purposes
sub num_common_items {
   my $mate_1 = shift;
   my $mate_2 = shift;
   my $param = shift;

   my @commons = common_items($mate_1, $mate_2, $param);

   return $#commons+1;
}

# This function checks if two input users are mates with each other by checking if their zids
# are present in the other's mates list in user.txt. It returns true if both are in each other's mate list
sub are_mates {
   my $mate_1 = shift;
   my $mate_2 = shift;
   my $are_mates = 0;

   # getting the mate lists of each user as a string
   $my_mate_list = find_in_file("$users_dir/$mate_1/user.txt","mates");
   $their_mate_list = find_in_file("$users_dir/$mate_2/user.txt","mates");

   # if they are both in each other's mates list
   if ($my_mate_list =~ /$mate_2/ && $their_mate_list =~ /$mate_1/){
      return 1;
   }

   return $are_mates
}

# This function gets the privacy setting of the input user based on the default setting for
# the parameter, or what was saved in their privacy file if it exists
sub get_privacy_setting {
   my $login_user = shift;
   my $param = shift;

   # if the privacy file exists, search it for the parameter setting
   if (-e "$users_dir/$login_user/privacy.txt"){
      $setting = find_in_file("$users_dir/$login_user/privacy.txt",$param);

   # Otherwise, go by the reasonable default privacy setting for each parameter
   } else {
      switch ($param){
         case "posts"           {$setting = "everyone"}
         case "mate_list"       {$setting = "everyone"}
         case "profile_text"    {$setting = "everyone"}
         case "program"         {$setting = "mates"}
         case "home_suburb"     {$setting = "mates"}
         case "email"           {$setting = "me"}
         case "birthday"        {$setting = "me"}
         case "home_latitude"   {$setting = "me"}
         case "home_longitude"  {$setting = "me"}
         case "courses"         {$setting = "me"}
      }
   }

   return $setting;
}

# This function determines whether the input login user is allowed to view a 'parameter' or element of
# the display user's profile depending on their privacy settings
sub privacy_permission {
   my $login_user = shift;
   my $display_user = shift;
   my $param = shift;
   $can_view = 0;

   # Checking for if any user details can be viewed
   if ($param eq "user_details"){
      $param_value = "me";
      foreach $deet ('program','home_suburb','email','birthday',
                                 'home_latitude','home_longitude','courses'){
         $set = get_privacy_setting($display_user,$deet);
         chomp $set;
         if ($set eq "everyone"){
            $param_value = $set;
         } elsif ($set eq "mates" and $param_value ne "everyone"){
            $param_value = $set;
         }
      }

   # Otherwise, just check on the individual detail
   } else {
      $param_value = get_privacy_setting($display_user,$param);
   }

   # Determining the privacy permission of the two users
   chomp $param_value;
   switch ($param_value){
      case "everyone" {$can_view = 1}
      case "mates" {$can_view = (are_mates($login_user,$display_user) || $login_user eq $display_user) ? 1 : 0}
      case "me" {$can_view = ($login_user eq $display_user) ? 1 : 0}
      else  {$can_view = 0}
   }

   return $can_view;
}

# This function returns whether an input user account already existing by checking if their folder exists
sub existing_user {
   my $login_user = shift;
   my @users = sort(glob("$users_dir/*"));
   $valid = 0;

   # Checking the account id to each user
   foreach $user (@users){
      $user =~ s/$users_dir\///;
      $valid = 1 if ($user =~ /^$login_user$/);
   }

   return $valid;
}

# This function checks the inactive status of a user who may have suspended their account
# and returns the status of the inactive.txt file where the suspend cookie data is stored
sub inactive {
   my $login_user = shift;
   my $is_inactive = "";

   # Checking for if the file exists, otherwise, they are assumed to be active
   if (-e "$users_dir/$login_user/inactive.txt"){
      $status = find_in_file("$users_dir/$login_user/inactive.txt","status");
      chomp $status;
      $is_inactive = $status;
   }
}

# This function defines the button html tags to use around a matelook user's thumbnail and
# full name based on whether their account is suspended or not. It returns the button tags as
# a link if the user isn't deactivated otherwise returns the bolded tags
sub active_user_link {
   my $login_user = shift;
   my $display_user = shift;

   # If both are active, return it as a link
   if (!inactive($login_user) and !inactive($display_user)){
      $button_on = <<eof;
      <button type="submit" name="display_user" value="$display_user" class="button">
eof
      $button_off = "</button>";

   # Otherwise, make the name bold with no link
   } else {
      $button_on = "<b style=\"padding-left: 10px\">";
      $button_off = "</b>";
   }

   return ($button_on, $button_off);
}

# This function sends an email taking in the parameters of the email header
sub send_mail {
   $to = shift;
   $from = shift;
   $subject = shift;
   $message = shift;

   open(EMAIL, "|/usr/sbin/sendmail -t");

   # Email Header
   print EMAIL "To: $to\n";
   print EMAIL "From: $from\n";
   print EMAIL "Subject: $subject\n\n";
   # Email Body
   print EMAIL $message;

   close(EMAIL);
   #source https://www.tutorialspoint.com/perl/perl_sending_email.htm
}

# HTML header placed at the top of every page
sub page_header {

    return <<eof
Content-Type: text/html;charset=utf-8

<!DOCTYPE html>
<html lang="en">
<head>
<title>matelook</title>
<link href="matelook.css" rel="stylesheet">
<script>
   document.createElement("aside");
   document.createElement("article");
   document.createElement("main");
   document.createElement("section");
   document.createElement("thumbnail");
   document.createElement("comment");
   document.createElement("post");
   document.createElement("nav");
</script>
</head>
eof
}

# HTML placed at the bottom of every page
# It includes all supplied parameter values as a HTML comment
# if global variable $debug is set
sub page_trailer {
    my $html = "";
    $html .= join("", map("<!-- $_=".param($_)." -->\n", param())) if $debug;
    $html .= end_html;
    return $html;
}

main();
