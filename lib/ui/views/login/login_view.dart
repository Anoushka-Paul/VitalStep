import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/app/app.dialogs.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/services/login_service.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'package:vital_step/ui/views/home/home_view.dart';

import 'login_viewmodel.dart';

class LoginView extends StackedView<LoginViewModel> {
  LoginView({Key? key}) : super(key: key);
  final _formKey = GlobalKey<FormState>();
  String _selectedUserType = 'Patient'; // Initial value for the dropdown
  String _email = 'a';
  String _password = '';

  double generalTextFontSize = 15;

  final List<String> _userTypes = ['Specialist', 'Patient'];

  @override
  Widget builder(
    BuildContext context,
    LoginViewModel viewModel,
    Widget? child,
  ) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: 20),
              Container(
                height: MediaQuery.of(context).size.height * 0.2,
                child: const Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Text(
                      "VITALSTEP",
                      style:
                          TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 6),
                    Text(
                      "Login",
                      style: TextStyle(
                        fontSize: 22,
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.vertical,
                  child: Column(
                    children: [
                      const SizedBox(height: 20),
                      Form(
                        key: _formKey,
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: <Widget>[
                            Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 8),
                                    child: Text(
                                      "User Type",
                                      style: TextStyle(
                                        fontSize: generalTextFontSize,
                                      ),
                                    ),
                                  ),
                                  DropdownButtonFormField<String>(
                                    value: _selectedUserType,
                                    decoration: const InputDecoration(
                                      labelText: 'Select User Type',
                                      fillColor:
                                          Color.fromARGB(33, 158, 158, 158),
                                      filled: true,
                                      enabledBorder: OutlineInputBorder(
                                        borderSide: BorderSide(
                                            color: Colors.transparent),
                                      ),
                                      focusedBorder: OutlineInputBorder(
                                        borderSide: BorderSide(
                                            color: Colors.transparent),
                                      ),
                                      floatingLabelBehavior:
                                          FloatingLabelBehavior.never,
                                    ),
                                    items: _userTypes.map((String userType) {
                                      return DropdownMenuItem<String>(
                                        value: userType,
                                        child: Text(userType),
                                      );
                                    }).toList(),
                                    onChanged: (newValue) {
                                      _selectedUserType = newValue!;
                                      viewModel.notifyListeners();
                                    },
                                    validator: (value) {
                                      if (value == null || value.isEmpty) {
                                        return 'Please select a user type';
                                      }
                                      return null;
                                    },
                                  ),
                                ]),
                            const SizedBox(height: 16),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Padding(
                                  padding: const EdgeInsets.only(bottom: 8),
                                  child: Text(
                                    "Email",
                                    style: TextStyle(
                                      fontSize: generalTextFontSize,
                                    ),
                                  ),
                                ),
                                TextFormField(
                                  decoration: InputDecoration(
                                    labelText: "Email",

                                    labelStyle: TextStyle(
                                        fontSize: generalTextFontSize),
                                    fillColor:
                                        const Color.fromARGB(33, 158, 158, 158),
                                    filled:
                                        true, // Ensures the background color is applied
                                    enabledBorder: const OutlineInputBorder(
                                      borderSide: BorderSide(
                                          color: Colors
                                              .transparent), // No border when enabled
                                    ),
                                    focusedBorder: const OutlineInputBorder(
                                      borderSide: BorderSide(
                                          color: Colors
                                              .transparent), // No border when focused
                                    ),
                                    floatingLabelBehavior: FloatingLabelBehavior
                                        .never, // Keeps the label always fixed
                                  ),
                                  onSaved: (value) {
                                    _email = value!;
                                  },
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Please enter your Email';
                                    }
                                    return null;
                                  },
                                ),
                              ],
                            ),
                            const SizedBox(height: 16),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Padding(
                                  padding: const EdgeInsets.only(bottom: 8),
                                  child: Text(
                                    "Password",
                                    style: TextStyle(
                                      fontSize: generalTextFontSize,
                                    ),
                                  ),
                                ),
                                TextFormField(
                                  decoration: InputDecoration(
                                      hintStyle: TextStyle(
                                          fontSize: generalTextFontSize),
                                      labelStyle: TextStyle(
                                          fontSize: generalTextFontSize),
                                      fillColor: const Color.fromARGB(
                                          33, 158, 158, 158),
                                      filled:
                                          true, // Ensures the background color is applied
                                      enabledBorder: const OutlineInputBorder(
                                        borderSide: BorderSide(
                                            color: Colors
                                                .transparent), // No border when enabled
                                      ),
                                      focusedBorder: const OutlineInputBorder(
                                        borderSide: BorderSide(
                                            color: Colors
                                                .transparent), // No border when focused
                                      ),
                                      labelText: 'Password',
                                      floatingLabelBehavior: FloatingLabelBehavior
                                          .never, // Keeps the label always fixed
                                      suffixIcon: IconButton(
                                        icon: Icon(viewModel.passwordVisible
                                            ? Icons.visibility
                                            : Icons.visibility_off),
                                        onPressed: () {
                                          viewModel.passwordVisible =
                                              !viewModel.passwordVisible;
                                          viewModel.rebuildUi();
                                        },
                                      )),
                                  obscureText: viewModel.passwordVisible,
                                  onSaved: (value) {
                                    _password = value!;
                                  },
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Please enter your password';
                                    }
                                    return null;
                                  },
                                ),
                              ],
                            ),
                            GestureDetector(
                              onTap: () async {
                                if (_formKey.currentState!.validate()) {
                                  _formKey.currentState!.save();
                                  final _loginService = locator<LoginService>();
                                  if (viewModel.isBusy) {
                                    return;
                                  }
                                  viewModel.setBusy(true);
                                  await _loginService.signIn(
                                      _email, _password, _selectedUserType);
                                  viewModel.setBusy(false);
                                }
                              },
                              child: Container(
                                height: 55,
                                margin: const EdgeInsets.only(top: 30),
                                width: double.infinity,
                                decoration: BoxDecoration(
                                  color: kcPrimaryColor,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: viewModel.isBusy
                                    ? const Center(
                                        child: CircularProgressIndicator(
                                          color: Colors.white,
                                        ),
                                      )
                                    : const Center(
                                        child: Text(
                                          'Login',
                                          style: TextStyle(
                                            fontSize: 16,
                                            color: Colors.white,
                                          ),
                                        ),
                                      ),
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.fromLTRB(10, 20, 10, 0),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text(
                                    "Forgot Password ?",
                                    style: TextStyle(
                                      fontSize: generalTextFontSize,
                                    ),
                                  ),
                                  const SizedBox(
                                    width: 5,
                                  ),
                                  GestureDetector(
                                    onTap: () {
                                      NavigationService()
                                          .navigateToPasswordResetViewView();
                                    },
                                    child: Text(
                                      "Reset Password",
                                      style: TextStyle(
                                          fontSize: generalTextFontSize,
                                          color: kcPrimaryColor,
                                          fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.fromLTRB(10, 5, 10, 0),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text(
                                    "New User?",
                                    style: TextStyle(
                                      fontSize: generalTextFontSize,
                                    ),
                                  ),
                                  const SizedBox(
                                    width: 5,
                                  ),
                                  GestureDetector(
                                    onTap: () {
                                      NavigationService()
                                          .navigateToSignUpView();
                                    },
                                    child: Text(
                                      "Sign Up",
                                      style: TextStyle(
                                          fontSize: generalTextFontSize,
                                          color: kcPrimaryColor,
                                          fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            verticalSpaceMedium,
                            Container(
                              padding: const EdgeInsets.fromLTRB(10, 5, 10, 0),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  GestureDetector(
                                    onTap: () {
                                      NavigationService()
                                          .navigateToSignUpSpecialistView();
                                    },
                                    child: Text(
                                      "Specialist Sign Up",
                                      style: TextStyle(
                                          fontSize: generalTextFontSize,
                                          color: kcPrimaryColor,
                                          fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ),
                            )
                          ],
                        ),
                      ),
                      const SizedBox(height: 40),
                    ],
                  ),
                ),
              )
            ],
          ),
        ),
      ),
    );
  }

  @override
  LoginViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      LoginViewModel();
}
