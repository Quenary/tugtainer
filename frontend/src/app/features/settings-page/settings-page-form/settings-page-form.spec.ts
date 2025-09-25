import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SettingsPageForm } from './settings-page-form';

describe('SettingsForm', () => {
  let component: SettingsPageForm;
  let fixture: ComponentFixture<SettingsPageForm>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SettingsPageForm]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SettingsPageForm);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
