import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked/stacked_annotations.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/Model/profile.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/ui/common/FormValidators.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/app_strings.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'package:vital_step/ui/views/sign_up/sign_up_view.form.dart';

import 'sign_up_viewmodel.dart';

@FormView(fields: [
  FormTextField(name: 'name', validator: FormValidators.nameValidator),
  FormTextField(
      name: 'mobile number', validator: FormValidators.mobileNumberValidator),
  FormTextField(name: 'email', validator: FormValidators.emailValidator),
  FormTextField(name: 'password', validator: FormValidators.passwordValidator),
  FormTextField(
      name: 'height', validator: FormValidators.heightInCentiMetersValidator),
  FormTextField(name: "accessCode"),
  FormTextField(name: "city"),
  FormTextField(name: "country"),
  FormTextField(name: "pincode"),
  FormTextField(name: "address"),
  FormTextField(name: "palmLength"),
  FormTextField(name: "palmWidth"),
  FormTextField(name: "countryCode"),
  FormTextField(name: "knucklesLength"),
  FormTextField(name: 'weight', validator: FormValidators.weightInKgValidator),
  FormDateField(name: 'dob'),
  FormDropdownField(items: [
    StaticDropdownItem(title: "Right", value: "Right"),
    StaticDropdownItem(title: "Left", value: "Left"),
  ], name: 'dominant hand'),
  FormDropdownField(items: [
    StaticDropdownItem(title: "Male", value: "Male"),
    StaticDropdownItem(title: "Female", value: "Female"),
    StaticDropdownItem(title: "prefer not to say", value: "Prefer not to say"),
    StaticDropdownItem(title: "Other", value: "Other"),
  ], name: "gender"),
  FormDropdownField(
      items: countryCodeDropDownItems, name: "countryCodesDropDown")
])
class SignUpView extends StackedView<SignUpViewModel> with $SignUpView {
  SignUpView({Key? key, this.profile}) : super(key: key);
  final Profile? profile;
  final inputStyle = InputDecoration(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10.0), // Add border radius
        borderSide: BorderSide.none, // Remove the default border
      ),
      fillColor: Colors.grey[200],
      filled: true);

  @override
  Widget builder(
    BuildContext context,
    SignUpViewModel viewModel,
    Widget? child,
  ) {
    final bool update = profile != null;
    return Scaffold(
      backgroundColor: Colors.white,
      body: Container(
        padding: const EdgeInsets.only(left: 25.0, right: 25.0),
        child: Form(
          key: viewModel.formKey,
          child: ListView(
            children: [
              SignUpHeader(update: update),
              TextFormField(
                controller: nameController,
                decoration: inputStyle.copyWith(labelText: 'Name[Required]'),
                validator: FormValidators.nameValidator,
              ),
              verticalSpaceSmall,

              const Text('CountryCode [Required] '),
              DropdownButton<String>(
                key: const ValueKey('countryCodesDropDownField'),
                value: viewModel.countryCodesDropDownValue,
                onChanged: (value) {
                  viewModel.setCountryCodesDropDown(value!);
                },
                isExpanded: true,
                items: CountryCodesDropDownValueToTitleMap.keys
                    .map(
                      (value) => DropdownMenuItem<String>(
                        key: ValueKey('$value key'),
                        value: value,
                        child:
                            Text(CountryCodesDropDownValueToTitleMap[value]!),
                      ),
                    )
                    .toList(),
              ),

              verticalSpaceSmall,
              TextFormField(
                controller: mobileNumberController,
                decoration:
                    inputStyle.copyWith(labelText: 'Mobile Number [Required]'),
                keyboardType: TextInputType.phone,
                validator: FormValidators.mobileNumberValidator,
                enabled: profile == null ? true : false,
              ),
              verticalSpaceSmall,
              TextFormField(
                controller: emailController,
                decoration: inputStyle.copyWith(labelText: 'Email [Required]'),
                keyboardType: TextInputType.emailAddress,
                validator: FormValidators.emailValidator,
                enabled: profile == null ? true : false,
              ),
              verticalSpaceSmall,
              TextFormField(
                controller: passwordController,
                decoration: InputDecoration(
                    labelText: 'Password [Required]',
                    border: InputBorder.none,
                    fillColor: Colors.grey[200],
                    filled: true,
                    suffixIcon: IconButton(
                      icon: Icon(viewModel.passwordVisible
                          ? Icons.visibility
                          : Icons.visibility_off),
                      onPressed: () {
                        viewModel.passwordVisible = !viewModel.passwordVisible;
                        viewModel.rebuildUi();
                      },
                    )),
                obscureText: viewModel.passwordVisible,
                validator: FormValidators.passwordValidator,
              ),
              verticalSpaceSmall,
              // address
              TextFormField(
                controller: addressController,
                decoration: inputStyle.copyWith(labelText: 'Address'),
              ),
              verticalSpaceSmall,
              // city
              TextFormField(
                controller: cityController,
                decoration: inputStyle.copyWith(labelText: 'City'),
              ),
              verticalSpaceSmall,
              // pincode
              TextFormField(
                controller: pincodeController,
                decoration: inputStyle.copyWith(labelText: 'pincode'),
                keyboardType: TextInputType.number,
              ),
              verticalSpaceSmall,
              TextFormField(
                controller: countryController,
                decoration: inputStyle.copyWith(labelText: 'Country'),
              ),
              verticalSpaceSmall,

              TextFormField(
                controller: viewModel.viewDobController,
                decoration:
                    inputStyle.copyWith(labelText: 'Date of Birth[Required]'),
                readOnly: true,
                onTap: () async {
                  viewModel.setDOB(context);
                },
              ),
              verticalSpaceSmall,
              TextFormField(
                controller: palmLengthController,
                decoration: inputStyle.copyWith(
                    labelText: 'Palm Length (cm)',
                    suffixIcon: IconButton(
                        onPressed: () {
                          showDialog(
                              context: context,
                              builder: (context) {
                                return Dialog(
                                  child: Image.asset(
                                    "assets/palmLength.png",
                                    width: 150,
                                    height: 150,
                                  ),
                                );
                              });
                        },
                        icon: const Icon(Icons.info_outline))),
                keyboardType: TextInputType.number,
              ),
              verticalSpaceSmall,
              // "palm_width": 9.5,
              TextFormField(
                controller: palmWidthController,
                decoration: inputStyle.copyWith(
                    labelText: 'Palm Width (cm)',
                    suffixIcon: IconButton(
                        onPressed: () {
                          showDialog(
                              context: context,
                              builder: (context) {
                                return Dialog(
                                  child: Image.asset(
                                    "assets/palmWidth.png",
                                    width: 150,
                                    height: 150,
                                  ),
                                );
                              });
                        },
                        icon: const Icon(Icons.info_outline))),
                keyboardType: TextInputType.number,
              ),
              verticalSpaceSmall,
              // "knuckles_length": 7.5,
              TextFormField(
                controller: knucklesLengthController,
                decoration: inputStyle.copyWith(
                    labelText: 'Knuckles Length (cm)',
                    suffixIcon: IconButton(
                        onPressed: () {
                          showDialog(
                              context: context,
                              builder: (context) {
                                return Dialog(
                                  child: Image.asset(
                                    "assets/knucleLength.png",
                                    width: 150,
                                    height: 150,
                                  ),
                                );
                              });
                        },
                        icon: const Icon(Icons.info_outline))),
                keyboardType: TextInputType.number,
              ),
              verticalSpaceSmall,
              TextFormField(
                controller: heightController,
                decoration:
                    inputStyle.copyWith(labelText: 'Height in CM [Required]'),
                validator: FormValidators.heightInCentiMetersValidator,
                keyboardType: TextInputType.number,
              ),
              verticalSpaceSmall,
              TextFormField(
                controller: weightController,
                decoration:
                    inputStyle.copyWith(labelText: 'Weight in KG [Required]'),
                validator: FormValidators.weightInKgValidator,
                keyboardType: TextInputType.number,
              ),
              verticalSpaceMedium,
              Row(
                children: [
                  // gender
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Gender [Required] '),
                        DropdownButton<String>(
                          key: const ValueKey('dropdownField'),
                          value: viewModel.genderValue,
                          onChanged: (value) {
                            viewModel.setGender(value!);
                          },
                          items: GenderValueToTitleMap.keys
                              .map(
                                (value) => DropdownMenuItem<String>(
                                  key: ValueKey('$value key'),
                                  value: value,
                                  child: Text(GenderValueToTitleMap[value]!),
                                ),
                              )
                              .toList(),
                        ),
                      ],
                    ),
                  ),
                  // dominant hand
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Dominant Hand [Required]'),
                        DropdownButton<String>(
                          key: const ValueKey('dominantHandField'),
                          value: viewModel.dominantHandValue,
                          onChanged: (value) {
                            viewModel.setDominantHand(value!);
                          },
                          items: DominantHandValueToTitleMap.keys
                              .map(
                                (value) => DropdownMenuItem<String>(
                                  key: ValueKey('$value key'),
                                  value: value,
                                  child:
                                      Text(DominantHandValueToTitleMap[value]!),
                                ),
                              )
                              .toList(),
                        ),
                      ],
                    ),
                  )
                ],
              ),
              verticalSpaceSmall,
              // Checkbox for terms and conditions
              profile == null
                  ? CheckboxListTile(
                      title: RichText(
                        text: TextSpan(
                          children: [
                            const TextSpan(
                              text: "I accept the ",
                              style: TextStyle(color: Colors.black),
                            ),
                            TextSpan(
                              text: "terms and conditions",
                              style: const TextStyle(
                                color: Colors.blue,
                                fontWeight: FontWeight.bold,
                                decoration: TextDecoration.underline,
                              ),
                              recognizer: TapGestureRecognizer()
                                ..onTap = () {
                                  NavigationService()
                                      .navigateToPrivacyPolicyView();
                                },
                            ),
                          ],
                        ),
                      ),
                      value: viewModel.isTermsAccepted,
                      onChanged: (newValue) {
                        viewModel.isTermsAccepted = newValue!;
                        viewModel.rebuildUi();
                      },
                      controlAffinity: ListTileControlAffinity.leading,
                    )
                  : SizedBox(),

              verticalSpaceSmall,
              InkWell(
                onTap: () async {
                  if (viewModel.isBusy) {
                    return;
                  }
                  if (profile == null) {
                    await viewModel.saveData(update: false);
                  } else if (profile != null) {
                    await viewModel.saveData(update: true);
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
                      : Center(
                          child: Text(
                            profile == null ? "Sign Up" : 'Update',
                            style: const TextStyle(
                              fontSize: 16,
                              color: Colors.white,
                            ),
                          ),
                        ),
                ),
              ),
              verticalSpaceSmall,
              profile == null ? const SignUpBottom() : const SizedBox()
            ],
          ),
        ),
      ),
    );
  }

  @override
  SignUpViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      SignUpViewModel();

  @override
  void onViewModelReady(SignUpViewModel viewModel) {
    syncFormWithViewModel(viewModel);
    if (profile != null) {
      viewModel.setProfile(profile!);
    }
  }

  @override
  void onDispose(SignUpViewModel viewModel) {
    disposeForm();
  }
}

class SignUpBottom extends StatelessWidget {
  const SignUpBottom({
    super.key,
  });
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 20),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text(
            "Already have an account?",
            style: TextStyle(
              fontSize: 15,
            ),
          ),
          const SizedBox(
            width: 5,
          ),
          GestureDetector(
            onTap: () {
              NavigationService().navigateToLoginView();
            },
            child: const Text(
              "Sign In",
              style: TextStyle(
                  fontSize: 15,
                  color: kcPrimaryColor,
                  fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }
}

class SignUpHeader extends StatelessWidget {
  const SignUpHeader({super.key, required this.update});
  final bool update;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        verticalSpaceLarge,
        Text(
          "VITALSTEP",
          style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
        ),
        verticalSpaceMedium,
        Text(
          update == true ? "Update" : "Sign Up",
          style: TextStyle(
            fontSize: 22,
          ),
        ),
        verticalSpaceLarge,
      ],
    );
  }
}
